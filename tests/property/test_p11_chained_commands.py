# Feature: kiro-agent-harness-template, Property 11: Chained commands block if any segment blocks
# Validates: kiro-agent-harness-template/R4.6
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests import _support  # noqa: F401
import destructive_guard
from destructive_guard import Pattern, check, tokenize

PATTERNS = [Pattern(t, tuple(tokenize(t))) for t in ("rm -rf /", "git push --force", "drop table")]
segments = st.lists(
    st.sampled_from(["rm -rf /", "rm -rf ./build", "git push --force", "git push origin", "DROP TABLE x",
                     "echo hi", "ls", "git status", "drop  database"]),
    min_size=1, max_size=5,
)
separators = st.sampled_from(["&&", "||", ";", "|", "\n", " && ", " ; "])


class ChainedCommands(unittest.TestCase):
    @given(segments, st.data())
    def test_joined_command_blocks_iff_some_segment_blocks(self, parts, data):
        command = parts[0]
        for part in parts[1:]:
            command += data.draw(separators) + part
        any_blocks = any(check(part, PATTERNS) is not None for part in parts)
        self.assertEqual(destructive_guard.check(command, PATTERNS) is not None, any_blocks, command)


if __name__ == "__main__":
    unittest.main()
