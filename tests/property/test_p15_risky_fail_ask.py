# Feature: kiro-agent-harness-template, Property 15: Risky guard asks when input or configuration is unusable
# Validates: kiro-agent-harness-template/R5.6, kiro-agent-harness-template/R5.7, kiro-agent-harness-template/R11.8
import io
import json
import tempfile
import unittest
from pathlib import Path

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests._support import POLICY, tool_call
import risky_guard

LIST = POLICY / "risky-tools.conf"


def not_json(data: bytes) -> bool:
    try:
        json.loads(data.decode("utf-8"))
        return False
    except (UnicodeDecodeError, ValueError):
        return True


bad_input = st.one_of(
    st.just(b""),
    st.binary(max_size=40).filter(not_json),
    st.dictionaries(st.sampled_from(["tool_input", "cwd", "x"]), st.text(max_size=5)).map(lambda d: json.dumps(d).encode()),
    st.just(json.dumps({"tool_name": "", "tool_input": {}}).encode()),
)
bad_lines = st.sampled_from([
    "delete_file only one part",
    "delete_file | missing match",
    "web_fetch | reason | regex url (unclosed",
    "web_fetch | reason | host-not-in url",
    "web_fetch | reason | sometimes",
    "two words | reason | *",
])


def decision(stdout):
    return json.loads(stdout.getvalue())["hookSpecificOutput"]


class RiskyFailAsk(unittest.TestCase):
    @given(bad_input)
    def test_unusable_input_asks(self, stdin):
        stdout, stderr = io.StringIO(), io.StringIO()
        self.assertEqual(risky_guard.main(io.BytesIO(stdin), stdout, stderr, LIST), 0)
        output = decision(stdout)
        self.assertEqual(output["permissionDecision"], "ask")
        self.assertIn("could not be parsed", output["permissionDecisionReason"])
        self.assertTrue(stderr.getvalue())

    @given(st.lists(st.sampled_from(["delete_file | ok | *", "# c", ""]), max_size=3), bad_lines, st.data())
    def test_unusable_list_asks_naming_the_file(self, good, bad, data):
        lines = list(good)
        lines.insert(data.draw(st.integers(0, len(lines))), bad)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "risky.conf"
            path.write_text("\n".join(lines) + "\n")
            stdout, stderr = io.StringIO(), io.StringIO()
            code = risky_guard.main(io.BytesIO(tool_call("read_file", {})), stdout, stderr, path)
        self.assertEqual(code, 0)
        output = decision(stdout)
        self.assertEqual(output["permissionDecision"], "ask")
        self.assertIn(str(path), output["permissionDecisionReason"])
        self.assertIn(str(path), stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
