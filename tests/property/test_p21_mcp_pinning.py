# Feature: kiro-agent-harness-template, Property 21: uvx packages must be pinned to an exact version
# Validates: kiro-agent-harness-template/R8.4
import re
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests.property._mcp_helpers import by_rule, check, entry

names = st.sampled_from(["mcp-server-fetch", "mcp-server-git", "awslabs.aws-documentation-mcp-server", "pkg"])
versions = st.tuples(st.integers(0, 2030), st.integers(0, 20), st.integers(0, 40)).map(lambda v: ".".join(map(str, v)))
specs = st.one_of(
    st.builds(lambda n, v: f"{n}@{v}", names, versions),
    names.map(lambda n: f"{n}@latest"),
    names,
    st.builds(lambda n, op, v: f"{n}{op}{v}", names, st.sampled_from(["==", ">=", "~=", "@^", "@~", "@>="]), versions),
    names.map(lambda n: f"{n}@1.*"),
    names.map(lambda n: f"{n}@1.2"),
    st.builds(lambda n, v, s: f"{n}@{v}{s}", names, versions, st.sampled_from(["rc1", "-beta", ".dev0", "a1"])),
)
GIT_FLOOR = (2026, 10, 28)


def reference_error(spec):
    match = re.fullmatch(r"([A-Za-z0-9._-]+)@(\d+)\.(\d+)\.(\d+)", spec)
    if not match:
        return True
    version = tuple(int(x) for x in match.groups()[1:])
    return match.group(1) == "mcp-server-git" and version < GIT_FLOOR


class McpPinning(unittest.TestCase):
    @given(specs, st.booleans())
    def test_error_iff_not_an_exact_pin_or_below_the_floor(self, spec, use_from):
        args = ["--from", spec, "tool"] if use_from else [spec]
        findings = by_rule(check({"svc": entry(args=args)}), "MCP-PIN")
        self.assertEqual(bool(findings), reference_error(spec), spec)


if __name__ == "__main__":
    unittest.main()
