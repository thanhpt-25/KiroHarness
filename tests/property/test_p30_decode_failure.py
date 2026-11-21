# Feature: agent-harness-platform, Property 30: Decode failure applies guard failure semantics
# Validates: agent-harness-platform/R4.4
import json
import unittest

from hypothesis import assume, given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests.property.strategies_core import AGENTS, adapter
import adapters
import guard_cli
import guards

garbage = st.one_of(
    st.binary(max_size=200),
    st.sampled_from([b"", b"   ", b"[]", b'"x"', b"null", b"{", b"\xff\xfe"]),
)


class DecodeFailure(unittest.TestCase):
    @given(st.sampled_from(AGENTS), st.sampled_from(["pre_tool", "prompt_submit"]), garbage)
    def test_undecodable_input_gives_each_guards_failure_decision(self, agent, trigger, raw):
        ad = adapter(agent)
        try:
            ad.decode(raw, trigger)
        except adapters.DecodeError:
            pass
        else:
            assume(False)  # decodable input is covered by Properties 29 and 31
        decisions = guards.run_guards(trigger, None, "bad input", None, ad.failure)
        for (name, _loader), decision in zip(guards.guards_for(trigger), decisions):
            self.assertEqual(decision.kind, adapters.failure_kind(name))
        code, out, err = guard_cli.run(agent, trigger, raw)
        if trigger == "pre_tool":  # destructive guard denies and wins over the risky guard's ask
            self.assertEqual((code, out), (2, ""))
            self.assertIn("destructive-command-guard", err)
        else:
            self.assertEqual((code, out), (2, ""))
            self.assertIn("prompt-secret-scan", err)


if __name__ == "__main__":
    unittest.main()
