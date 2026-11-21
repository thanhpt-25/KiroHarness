# Feature: agent-harness-platform, Property 42: Traceability_Report completeness
# Validates: agent-harness-platform/R13.5
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests import _support  # noqa: F401
from harness_validator import trace_check

ids = st.sampled_from([f"{n}.{m}" for n in range(1, 5) for m in range(1, 4)])


class Traceability(unittest.TestCase):
    @given(known=st.sets(ids, min_size=1), tagged=st.sets(ids))
    def test_uncovered_and_dangling_partition(self, known, tagged):
        tags = [("t.py", 1, "s", i) for i in tagged]
        uncovered, dangling = trace_check.analyze({"s": known}, tags, [])
        self.assertEqual(set(uncovered), {f"s/R{i}" for i in known - tagged})
        self.assertEqual({d[2] for d in dangling}, {f"s/R{i}" for i in tagged - known})

    @given(known=st.sets(ids, min_size=1))
    def test_record_covers_like_a_tag(self, known):
        records = [("r.md", "s", i) for i in known]
        self.assertEqual(trace_check.analyze({"s": known}, [], records), ([], []))


if __name__ == "__main__":
    unittest.main()
