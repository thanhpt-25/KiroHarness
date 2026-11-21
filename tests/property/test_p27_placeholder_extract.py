# Feature: kiro-agent-harness-template, Property 27: Placeholder extraction matches the placeholder format
# Validates: kiro-agent-harness-template/R2.7
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests import _support  # noqa: F401
from harness_validator.placeholders import find_placeholders

UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
valid_names = st.builds(lambda a, b: a + b, st.sampled_from(UPPER), st.text(alphabet=UPPER + "0123456789_", max_size=63))


def wrap(name):
    return "{{" + name + "}}"


near_misses = st.one_of(
    valid_names.map(lambda n: wrap(n.lower() + "a")),
    valid_names.map(lambda n: wrap("1" + n)),
    valid_names.map(lambda n: wrap("_" + n)),
    st.just(wrap("A" * 65)),
    valid_names.map(lambda n: "{" + n + "}"),
    valid_names.map(lambda n: wrap(" " + n)),
    valid_names.map(lambda n: wrap(n[:1] + " " + n[1:] + "X")),
)
filler = st.text(alphabet="abc xyz.\n-", max_size=10)


class PlaceholderExtract(unittest.TestCase):
    @given(st.lists(st.tuples(st.booleans(), valid_names, near_misses, filler), max_size=8))
    def test_returns_exactly_the_valid_placeholders(self, parts):
        text, expected = "", set()
        for use_valid, name, miss, gap in parts:
            if use_valid:
                text += gap + wrap(name) + gap
                expected.add(name)
            else:
                text += gap + miss + gap
        self.assertEqual(find_placeholders(text), expected)


if __name__ == "__main__":
    unittest.main()
