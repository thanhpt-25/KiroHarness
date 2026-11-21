# Feature: kiro-agent-harness-template, Property 17: Command configuration predicate
import re
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests import _support  # noqa: F401
from quality import is_configured

placeholder = st.from_regex(r"\A[A-Z][A-Z0-9_]{0,10}\Z").map(lambda n: "{{" + n + "}}")
values = st.one_of(
    st.text(max_size=20),
    st.text(alphabet=" \t\n", max_size=5),
    st.builds(lambda a, p, b: a + p + b, st.text(max_size=8), placeholder, st.text(max_size=8)),
)


class IsConfigured(unittest.TestCase):
    @given(values)
    def test_true_iff_non_blank_and_no_placeholder(self, value):
        expected = value.strip() != "" and re.search(r"\{\{[A-Z][A-Z0-9_]{0,63}\}\}", value) is None
        self.assertEqual(is_configured(value), expected)

    def test_none_is_not_configured(self):
        self.assertFalse(is_configured(None))


if __name__ == "__main__":
    unittest.main()
