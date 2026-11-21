# Feature: agent-harness-platform, Property 43: EARS classification
# Validates: agent-harness-platform/R13.2
import string
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests import _support  # noqa: F401
from harness_validator import spec_lint
from tests.property.test_p41_task_refs import requirements_text
from tests.validator.test_spec_lint import good_files

words = st.text(alphabet=string.ascii_lowercase + " ,.", min_size=0, max_size=40)
clause = st.builds(lambda kw, w: f"{kw} {w}".strip(), st.sampled_from(["WHEN", "WHILE", "IF", "WHERE"]), words)
ears = st.builds(lambda pre, w: ", ".join([*pre, "THE system SHALL " + w]), st.lists(clause, max_size=3), words)
other_start = st.text(alphabet=string.ascii_letters + string.digits + " ", min_size=1, max_size=40).filter(
    lambda s: s.strip() and not spec_lint.EARS_START.match(s.strip()))


def lint(criterion):
    files = good_files()
    files["requirements.md"] = requirements_text([1]).replace("THE System SHALL do 1.1.", criterion)
    return [f for f in spec_lint.check_spec("s", files) if f.rule == "SPEC-EARS"]


class EarsClassification(unittest.TestCase):
    @given(ears)
    def test_ears_grammar_strings_are_accepted(self, text):
        self.assertTrue(spec_lint.is_ears(text))
        self.assertEqual(lint(text), [])

    @given(other_start)
    def test_strings_without_a_keyword_start_are_errors(self, text):
        self.assertFalse(spec_lint.is_ears(text))
        self.assertEqual(len(lint(text)), 1)


if __name__ == "__main__":
    unittest.main()
