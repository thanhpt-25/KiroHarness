# Feature: agent-harness-platform, Property 44: Policy_File parse round trip
# Validates: agent-harness-platform/R5.1, agent-harness-platform/R5.4
import string
import tempfile
import unittest
from pathlib import Path

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests import _support  # noqa: F401
import destructive_guard
import risky_guard

word = st.text(alphabet=string.ascii_lowercase + string.digits + "_-.", min_size=1, max_size=8)
host = st.text(alphabet=string.ascii_lowercase + string.digits, min_size=1, max_size=3).flatmap(
    lambda head: st.text(alphabet=string.ascii_lowercase + string.digits + "-.", max_size=6).map(lambda tail: head + tail)
)  # a host starts with a letter or digit; "." alone is not a host
tools = st.one_of(
    st.sampled_from(["category:shell", "category:delete", "category:web", "claude-code:Bash", "kiro:execute_bash", "delete_file", "@git/git_reset"]),
    word,
)
reasons = st.text(alphabet=string.ascii_letters + " ,.", min_size=1, max_size=20).map(str.strip).filter(bool)
regexes = st.text(alphabet=string.ascii_lowercase + r"\b()|?.*+", min_size=1, max_size=12).filter(
    lambda r: _compiles(r) and not r.strip() == "" and " " not in r
)


def _compiles(pattern):
    import re

    try:
        re.compile(pattern)
        return True
    except re.error:
        return False


matches = st.one_of(
    st.just("*"),
    st.builds(lambda f, r: f"regex {f} {r}", word, regexes),
    st.builds(lambda f, hosts: f"host-not-in {f} " + " ".join(hosts), word, st.lists(host, min_size=1, max_size=3)),
)
risky_lines = st.lists(st.builds(lambda t, r, m: f"{t} | {r} | {m}", tools, reasons, matches), min_size=1, max_size=6)


def comparable(entry):
    match = entry.match
    detail = (type(match).__name__, getattr(match, "field", None),
              getattr(getattr(match, "regex", None), "pattern", None), tuple(sorted(getattr(match, "hosts", ()))))
    return entry.tool, entry.reason, detail


class PolicyRoundTrip(unittest.TestCase):
    @given(risky_lines)
    def test_risky_list(self, lines):
        entries = risky_guard.parse_list("\n".join(lines))
        again = risky_guard.parse_list(risky_guard.format_list(entries))
        self.assertEqual([comparable(e) for e in again], [comparable(e) for e in entries])

    @given(st.lists(st.text(alphabet=string.ascii_lowercase + " -/", min_size=1, max_size=20).filter(lambda s: s.strip()), min_size=1, max_size=10))
    def test_destructive_list(self, lines):
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp, "a.txt"), Path(tmp, "b.txt")
            first.write_text("\n".join(lines) + "\n")
            try:
                patterns = destructive_guard.load_patterns(first)
            except destructive_guard.ListLoadError:
                return  # no usable pattern in this draw
            second.write_text(destructive_guard.format_list(patterns))
            self.assertEqual(destructive_guard.load_patterns(second), patterns)


if __name__ == "__main__":
    unittest.main()
