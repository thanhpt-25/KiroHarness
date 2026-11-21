# Feature: kiro-agent-harness-template, Property 23: Env example covers every Secret_Reference
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests.property._mcp_helpers import by_rule, check, entry

VARS = ["ALPHA_TOKEN", "BETA_KEY", "GAMMA_SECRET", "DELTA_PASSWORD"]


@st.composite
def cases(draw):
    referenced = draw(st.lists(st.sampled_from(VARS), unique=True, min_size=1))
    servers = {}
    owner = {}
    for var in referenced:
        server = draw(st.sampled_from(["svc-a", "svc-b"]))
        owner[var] = server
        servers.setdefault(server, entry(disabled=True, env={}))["env"][var] = "${" + var + "}"
    lines, expected = [], set()
    for var in VARS:
        count = draw(st.integers(0, 2))
        comment = draw(st.booleans())
        for _ in range(count):
            if comment:
                lines.append(f"# Used by MCP server: {owner.get(var, 'other')}")
            lines.append(f"{var}=replace-me")
            lines.append("")
        if var in referenced and (count == 0 or count > 1 or not comment):
            expected.add(var)
    return servers, "\n".join(lines), expected, owner


class EnvExampleCoverage(unittest.TestCase):
    @given(cases())
    def test_errors_for_exactly_the_uncovered_variables(self, case):
        servers, env_text, expected, owner = case
        findings = by_rule(check(servers, env_text), "MCP-ENV-EXAMPLE")
        reported = {var for f in findings for var in VARS if f"variable {var} " in f.message}
        self.assertEqual(reported, expected, env_text)
        for f in findings:
            if "is not listed" in f.message:
                var = next(v for v in VARS if f"variable {v} " in f.message)
                self.assertIn(f'"{owner[var]}"', f.message)


if __name__ == "__main__":
    unittest.main()
