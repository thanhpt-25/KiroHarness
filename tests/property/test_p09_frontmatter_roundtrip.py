# Feature: kiro-agent-harness-template, Property 9: Front matter round trip for the supported YAML subset
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests import _support  # noqa: F401
from harness_validator.frontmatter import dump_front_matter, parse_front_matter

keys = st.from_regex(r"\A[A-Za-z_][A-Za-z0-9_-]{0,10}\Z")
strings = st.one_of(
    st.text(max_size=20),
    st.sampled_from(["a: b", "x #y", "{a}", "  lead", "trail ", "true", "-", "[x]", "'q'", '"d"', "a,b", "#", "~", "null"]),
)
values = st.one_of(st.booleans(), strings, st.lists(strings, max_size=4))


class FrontMatterRoundTrip(unittest.TestCase):
    @given(st.dictionaries(keys, values, max_size=6))
    def test_dump_then_parse_returns_an_equal_mapping(self, data):
        self.assertEqual(parse_front_matter(dump_front_matter(data)), data)


if __name__ == "__main__":
    unittest.main()
