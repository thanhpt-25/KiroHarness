# Feature: kiro-agent-harness-template, Property 14: Risky guard agrees with the reference decision
import io
import json
import re
import tempfile
import unittest
from pathlib import Path

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests._support import tool_call
import risky_guard

TOOLS = ["delete_file", "web_fetch", "execute_bash"]
HOSTS = ["kiro.dev", "pypi.org", "example.com"]


@st.composite
def risky_lists(draw):
    entries = []
    for _ in range(draw(st.integers(1, 4))):
        tool = draw(st.sampled_from(TOOLS))
        kind = draw(st.sampled_from(["*", "regex", "host"]))
        if kind == "*":
            entries.append((tool, "*", None))
        elif kind == "regex":
            word = draw(st.sampled_from(["deploy", "rm", "publish"]))
            entries.append((tool, f"regex command \\b{word}\\b", ("regex", word)))
        else:
            hosts = draw(st.lists(st.sampled_from(HOSTS), min_size=1, unique=True))
            entries.append((tool, "host-not-in url " + " ".join(hosts), ("host", hosts)))
    return entries


calls = st.tuples(
    st.sampled_from(TOOLS + ["read_file"]),
    st.fixed_dictionaries({}, optional={
        "command": st.sampled_from(["cdk deploy", "rm a", "ls", "npm publish", "rmdir x"]),
        "url": st.sampled_from(["https://kiro.dev/x", "https://docs.pypi.org/", "http://example.com", "ftp://kiro.dev",
                                "not a url", "https://evil.com", "https://kiro.dev.evil.com"]),
    }),
)


def reference(entries, tool, tool_input):
    """Return the index of the first entry that matches, written independently of risky_guard."""
    for index, (entry_tool, _, condition) in enumerate(entries):
        if entry_tool != tool:
            continue
        if condition is None:
            return index
        if condition[0] == "regex":
            if "command" in tool_input and re.search(rf"\b{condition[1]}\b", tool_input["command"]):
                return index
            continue
        url = tool_input.get("url", "")
        allowed = False
        for scheme in ("http://", "https://"):
            if url.startswith(scheme):
                host = url[len(scheme):].split("/")[0].split(":")[0].lower()
                allowed = any(host == h or host.endswith("." + h) for h in condition[1])
        if not allowed:
            return index
    return None


class RiskyReference(unittest.TestCase):
    @given(risky_lists(), calls)
    def test_ask_iff_the_reference_finds_an_entry(self, entries, call):
        tool, tool_input = call
        lines = [f"{t} | reason {i} | {m}" for i, (t, m, _) in enumerate(entries)]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "risky.conf"
            path.write_text("\n".join(lines) + "\n")
            stdout, stderr = io.StringIO(), io.StringIO()
            code = risky_guard.main(io.BytesIO(tool_call(tool, tool_input)), stdout, stderr, path)
        self.assertEqual(code, 0)
        expected = reference(entries, tool, tool_input)
        if expected is None:
            self.assertEqual(stdout.getvalue(), "")
        else:
            output = json.loads(stdout.getvalue())["hookSpecificOutput"]
            self.assertEqual(output["permissionDecision"], "ask")
            self.assertIn(tool, output["permissionDecisionReason"])
            self.assertIn(lines[expected], output["permissionDecisionReason"])


if __name__ == "__main__":
    unittest.main()
