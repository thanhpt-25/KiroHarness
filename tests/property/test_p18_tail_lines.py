# Feature: kiro-agent-harness-template, Property 18: Output truncation keeps the last 200 lines
# Validates: kiro-agent-harness-template/R6.6
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests import _support  # noqa: F401
from runner import tail_lines

line_bodies = st.text(alphabet="abc xyz\t\u00e9", max_size=8)
lines = st.lists(st.tuples(line_bodies, st.sampled_from(["\n", "\r\n"])), max_size=1000)


class TailLines(unittest.TestCase):
    @given(lines, st.booleans())
    def test_keeps_the_last_200_lines_unchanged(self, items, unterminated_last):
        rendered = [body + end for body, end in items]
        if unterminated_last and rendered and items[-1][0]:
            rendered[-1] = items[-1][0]
        text = "".join(rendered)
        self.assertEqual(tail_lines(text, 200), "".join(rendered[-200:]))


if __name__ == "__main__":
    unittest.main()
