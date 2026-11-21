# Feature: kiro-agent-harness-template, Property 20: Credential values in MCP env must be Secret_References
# Validates: kiro-agent-harness-template/R8.3
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests.property._mcp_helpers import by_rule, check, entry

credential_keys = st.sampled_from(["API_KEY", "GITHUB_TOKEN", "CLIENT_SECRET", "DB_PASSWORD", "AWS_CREDENTIALS", "AUTH_HEADER"])
plain_keys = st.sampled_from(["LOG_LEVEL", "REGION", "PARTITION", "TIMEOUT_MS"])
valid_ref = st.from_regex(r"\A[A-Z][A-Z0-9_]{0,63}\Z").map(lambda n: "${" + n + "}")
invalid_ref = st.one_of(
    st.just("${lowercase}"), st.just("${1LEADING}"), st.just("${" + "A" * 65 + "}"), st.just("$NOBRACES"),
    st.just("{MISSING_DOLLAR}"), st.text(alphabet="abc123-", min_size=1, max_size=12),
)


class McpSecretRefs(unittest.TestCase):
    @given(st.dictionaries(st.one_of(credential_keys, plain_keys), st.one_of(valid_ref, invalid_ref), max_size=6))
    def test_error_iff_credential_key_holds_a_non_reference(self, env):
        findings = by_rule(check({"svc": entry(env=env)}), "MCP-SECRET-REF")
        expected = {
            f"mcpServers.svc.env.{key}"
            for key, value in env.items()
            if any(w in key.lower() for w in ("key", "token", "secret", "password", "credential", "auth"))
            and not (value.startswith("${") and value.endswith("}") and value[2:3].isupper()
                     and len(value) <= 67 and all(c.isupper() or c.isdigit() or c == "_" for c in value[2:-1]))
        }
        self.assertEqual({f.field for f in findings}, expected)


if __name__ == "__main__":
    unittest.main()
