# Feature: agent-harness-platform, Property 33: Unknown tools with command fields ask
# Validates: agent-harness-platform/R4.5
import string
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests.property.strategies_core import AGENTS, CAPS, adapter, words
import adapters
import event_model
import guards

COMMAND_FIELDS = {m["command"] for a in CAPS["agents"].values() for m in a["tool_map"].values() if "command" in m}
names = st.text(alphabet=string.ascii_letters + "_", min_size=1, max_size=12).filter(
    lambda n: all(n not in a["tool_map"] and not any(n.startswith(p) for p in a["tool_prefix_map"]) for a in CAPS["agents"].values())
)


def decide(agent, tool, tool_input):
    ad = adapter(agent)
    raw = ad.build_native_payload(adapters.HarnessEvent(agent=agent, trigger="pre_tool", tool_id=tool, tool_input=tool_input, cwd="/WORKSPACE"))
    event = ad.decode(raw, "pre_tool")
    return event, event_model.combine(guards.run_guards("pre_tool", event, None, None, ad.failure))


class UnknownTools(unittest.TestCase):
    @given(st.sampled_from(AGENTS), names, st.sampled_from(sorted(COMMAND_FIELDS)), st.text(alphabet=string.ascii_lowercase + " ", min_size=1, max_size=20))
    def test_unmapped_tool_with_a_command_field_asks(self, agent, tool, field, value):
        event, decision = decide(agent, tool, {field: value})
        self.assertEqual(event.category, "other")
        self.assertEqual(decision.kind, "ask")

    @given(st.sampled_from(AGENTS), names)
    def test_unmapped_tool_without_a_command_field_is_allowed(self, agent, tool):
        _event, decision = decide(agent, tool, {"note": "x"})
        self.assertEqual(decision.kind, "allow")


if __name__ == "__main__":
    unittest.main()
