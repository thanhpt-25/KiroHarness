# Feature: kiro-agent-harness-template, Property 8: Steering front matter validation
# Validates: kiro-agent-harness-template/R2.6, kiro-agent-harness-template/R2.9, kiro-agent-harness-template/R2.10, kiro-agent-harness-template/R2.11, kiro-agent-harness-template/R10.2, kiro-agent-harness-template/R10.3
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests import _support  # noqa: F401
from harness_validator.frontmatter import dump_front_matter
from harness_validator.steering import check_steering

MODES = ["always", "fileMatch", "manual", "auto"]
inclusions = st.one_of(st.sampled_from(MODES), st.sampled_from(["Always", "FILEMATCH", "Auto", "", "on"]),
                       st.text(alphabet="abcxyz", min_size=1, max_size=6))
patterns = st.one_of(st.none(), st.just(""), st.just([]), st.just(["**/*.py", ""]), st.just("**/*.ts"),
                     st.just(["**/*.ts", "src/**"]))
lengths = st.sampled_from([None, 0, 1, 64, 65, 200, 201])


def text_of(length):
    return None if length is None else "x" * length


@st.composite
def steering_files(draw):
    if not draw(st.booleans()):
        return "# No front matter\n", {"front_matter"}
    data = {}
    inclusion = draw(st.none() | inclusions)
    pattern, name, description = draw(patterns), text_of(draw(lengths)), text_of(draw(lengths))
    if inclusion is not None:
        data["inclusion"] = inclusion
    if pattern is not None:
        data["fileMatchPattern"] = pattern
    if name is not None:
        data["name"] = name
    if description is not None:
        data["description"] = description

    expected = set()
    if inclusion is None or inclusion not in MODES:
        expected.add("front_matter.inclusion")
    elif inclusion == "fileMatch":
        if pattern is None or pattern in ("", []) or (isinstance(pattern, list) and "" in pattern):
            expected.add("front_matter.fileMatchPattern")
    elif inclusion == "auto":
        if name is None or not 1 <= len(name) <= 64:
            expected.add("front_matter.name")
        if description is None or not 1 <= len(description) <= 200:
            expected.add("front_matter.description")
    return f"---\n{dump_front_matter(data)}---\n\n# Body\n", expected


class SteeringValidation(unittest.TestCase):
    @given(steering_files())
    def test_errors_exactly_for_invalid_front_matter(self, case):
        text, expected = case
        findings = check_steering(".kiro/steering/x.md", text)
        self.assertEqual({f.field for f in findings}, expected, text)
        self.assertTrue(all(f.path == ".kiro/steering/x.md" for f in findings))


if __name__ == "__main__":
    unittest.main()
