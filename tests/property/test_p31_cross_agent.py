# Feature: agent-harness-platform, Property 31: Cross-agent decision equivalence
# Validates: agent-harness-platform/R5.3
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests.property.strategies_core import AGENTS, CAPS, adapter, words
import adapters
import capabilities
import event_model
import guards

URLS = ["https://example.com/x", "https://pypi.org/simple", "https://docs.aws.amazon.com/", "ftp://example.com", "not a url"]


def tool_for(agent, category):
    tools = capabilities.tools_in_category(CAPS["agents"][agent], category)
    return tools[0] if tools else None


def decide(agent, tool, tool_input):
    ad = adapter(agent)
    raw = ad.build_native_payload(adapters.HarnessEvent(agent=agent, trigger="pre_tool", tool_id=tool, tool_input=tool_input, cwd="/WORKSPACE"))
    event = ad.decode(raw, "pre_tool")
    decisions = guards.run_guards("pre_tool", event, None, None, ad.failure)
    return event_model.combine(decisions)


class CrossAgent(unittest.TestCase):
    def check(self, category, field_for, value):
        agents = [a for a in AGENTS if tool_for(a, category)]
        self.assertGreaterEqual(len(agents), 2)
        results = []
        for agent in agents:
            mapping = CAPS["agents"][agent]["tool_map"][tool_for(agent, category)]
            results.append(decide(agent, tool_for(agent, category), {mapping[field_for]: value}))
        first = results[0]
        for other in results[1:]:
            self.assertEqual((other.kind, other.guard, other.matched), (first.kind, first.guard, first.matched))

    @given(words)
    def test_shell_commands_get_the_same_decision(self, command):
        self.check("shell", "command", command)

    @given(st.sampled_from(URLS))
    def test_web_fetches_get_the_same_decision(self, url):
        self.check("web", "url", url)


if __name__ == "__main__":
    unittest.main()
