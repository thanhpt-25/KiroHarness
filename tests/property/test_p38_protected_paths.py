# Feature: agent-harness-platform, Property 38: Protected-path decisions
# Validates: agent-harness-platform/R11.1, agent-harness-platform/R11.2
import re
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests import _support  # noqa: F401
import guards
import protected_paths
from event_model import HarnessEvent

LINES = [".env", ".env.*", "!.env.example", "*.pem", "id_rsa*", ".ssh/", ".aws/credentials", "secrets/*.txt", "!secrets/ok.txt",
         "build/", "k?y", "!build/keep.txt", "src/*.cfg", "a/b/c.key", "*.key"]
NAMES = [".env", ".env.local", ".env.example", "a.pem", "id_rsa", "id_rsa.pub", ".ssh", ".aws", "credentials", "secrets", "ok.txt",
         "x.txt", "build", "keep.txt", "key", "kay", "src", "a", "b", "c.key", "app.cfg", "ENV", ".ENV", "Credentials"]


def reference(lines, path):
    """Independent matcher: each rule becomes a regex over the lowercased, '/'-joined path."""
    def glob(part):
        return "".join("[^/]*" if c == "*" else "[^/]" if c == "?" else re.escape(c) for c in part)

    protected = False
    text = path.lower()
    for line in lines:
        negated = line.startswith("!")
        body = (line[1:] if negated else line).lower()
        dir_only = body.endswith("/")
        parts = [p for p in body.split("/") if p]
        core = "/".join(glob(p) for p in parts)
        if len(parts) == 1 and not dir_only:
            regex = rf"(^|/){core}$"
        else:
            regex = rf"(^|/){core}(/|$)"
        if re.search(regex, text):
            protected = not negated
    return protected


class ProtectedPaths(unittest.TestCase):
    @given(st.lists(st.sampled_from(LINES), min_size=1, max_size=8), st.lists(st.sampled_from(NAMES), min_size=1, max_size=4),
           st.sampled_from(["read", "write", "delete"]))
    def test_deny_exactly_when_the_reference_matcher_protects_the_path(self, lines, parts, category):
        positives = [l for l in lines if not l.startswith("!")]
        if not positives:
            return
        rules = protected_paths.parse_list("\n".join(lines))
        path = "/".join(parts)
        event = HarnessEvent(agent="kiro", trigger="pre_tool", tool_id="t", category=category, paths=(path,))
        decision = guards.evaluate_protected(event, rules, "list")
        self.assertEqual(decision.kind == "deny", reference(lines, path), (lines, path))
        if decision.kind == "deny":
            self.assertIn(path, decision.reason)


if __name__ == "__main__":
    unittest.main()
