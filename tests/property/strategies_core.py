"""Hypothesis strategies for the agent-neutral core (Properties 29 to 33)."""

import string

from hypothesis import strategies as st

from tests import _support  # noqa: F401  (puts harness/core on sys.path)
import adapters
import capabilities

CAPS = capabilities.load_capabilities()
AGENTS = sorted(CAPS["agents"])

text = st.text(alphabet=string.ascii_letters + string.digits + " ./_-:", min_size=1, max_size=30)
words = st.sampled_from(["ls", "echo hi", "git status", "rm -rf /", "git push --force", "DROP TABLE x", "terraform apply",
                         "npm publish", "rm build.log", "cat README.md", "git push origin main"])


def adapter(agent):
    return adapters.Adapter(agent, CAPS["agents"][agent])


@st.composite
def native_payloads(draw, trigger=None):
    """``(agent, trigger, raw bytes)`` for a payload the Agent could send."""
    agent = draw(st.sampled_from(AGENTS))
    entry = CAPS["agents"][agent]
    trigger = trigger or draw(st.sampled_from(["pre_tool", "prompt_submit"]))
    ad = adapter(agent)
    if trigger == "prompt_submit":
        event = adapters.HarnessEvent(agent=agent, trigger=trigger, prompt=draw(text), cwd="/WORKSPACE")
        return agent, trigger, ad.build_native_payload(event)
    kind = draw(st.sampled_from(["mapped", "unmapped", "prefix"]))
    if kind == "mapped":
        tool = draw(st.sampled_from(sorted(entry["tool_map"])))
        mapping = entry["tool_map"][tool]
        tool_input = {}
        if "command" in mapping:
            tool_input[mapping["command"]] = draw(words)
        for field in mapping.get("paths", []):
            tool_input[field] = draw(text)
        if "url" in mapping:
            tool_input[mapping["url"]] = "https://" + draw(st.sampled_from(["example.com", "pypi.org", "docs.aws.amazon.com"])) + "/x"
    elif kind == "prefix":
        prefix = sorted(entry["tool_prefix_map"])[0]
        tool = prefix + draw(st.text(alphabet=string.ascii_lowercase + "_/", min_size=1, max_size=12))
        tool_input = draw(st.dictionaries(st.sampled_from(["a", "b", "repo_path"]), text, max_size=2))
    else:
        tool = "unmapped_" + draw(st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=8))
        tool_input = draw(st.dictionaries(st.sampled_from(["command", "path", "q"]), words, max_size=3))
    event = adapters.HarnessEvent(agent=agent, trigger=trigger, tool_id=tool, tool_input=tool_input, cwd="/WORKSPACE")
    return agent, trigger, ad.build_native_payload(event)
