# Feature: agent-harness-platform, Property 41: Spec_Linter task references
# Validates: agent-harness-platform/R13.4
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests import _support  # noqa: F401
from harness_validator import spec_lint
from tests.validator.test_spec_lint import good_files


def requirements_text(counts):
    parts = ["# R\n\n## Introduction\n\nx\n\n## Glossary\n\n- **A**: b\n\n## Requirements\n"]
    for n, count in enumerate(counts, start=1):
        parts.append(f"\n### Requirement {n}: T{n}\n\n**User Story:** As a user, I want x, so that y.\n\n#### Acceptance Criteria\n\n")
        parts.append("".join(f"{m}. THE System SHALL do {n}.{m}.\n" for m in range(1, count + 1)))
    return "".join(parts)


@st.composite
def specs(draw):
    counts = draw(st.lists(st.integers(1, 4), min_size=1, max_size=4))
    ids = [f"{n}.{m}" for n, c in enumerate(counts, 1) for m in range(1, c + 1)]
    existing = draw(st.lists(st.sampled_from(ids), unique=True, max_size=len(ids)))
    missing = draw(st.lists(st.sampled_from([f"{n}.{m}" for n in range(1, 7) for m in range(5, 9)]), unique=True, max_size=4))
    return counts, ids, existing, missing


class TaskReferences(unittest.TestCase):
    @given(specs())
    def test_errors_for_exactly_the_missing_ids_and_warnings_for_exactly_the_unreferenced(self, spec):
        counts, ids, existing, missing = spec
        files = good_files()
        files["requirements.md"] = requirements_text(counts)
        lines = [f"- [ ] {i}. task\n  - _Requirements: {ref}_\n" for i, ref in enumerate(existing + missing, start=1)]
        files["tasks.md"] = "# Plan\n\n" + "".join(lines)
        found = spec_lint.check_spec("s", files)
        errs = sorted(f.message.split()[3].rstrip(",") for f in found if f.rule == "SPEC-TASKREF")
        warns = sorted(f.message.split()[1] for f in found if f.rule == "SPEC-UNREF")
        self.assertEqual(errs, sorted(missing))
        self.assertEqual(warns, sorted(set(ids) - set(existing)))
        self.assertEqual([f for f in found if f.rule not in ("SPEC-TASKREF", "SPEC-UNREF")], [])


if __name__ == "__main__":
    unittest.main()
