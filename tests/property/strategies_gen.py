"""Hypothesis strategies for the Generator (Properties 34 to 37)."""

import copy

from hypothesis import strategies as st

from tests.generator._fixture import MANIFEST

AGENT_NAMES = sorted(MANIFEST["agents"])
MCP_NAMES = sorted(MANIFEST["mcp"])


@st.composite
def manifests(draw):
    manifest = copy.deepcopy(MANIFEST)
    for agent in AGENT_NAMES:
        manifest["agents"][agent]["enabled"] = draw(st.booleans())
    manifest["agents_md"] = draw(st.booleans())
    for guard in manifest["guards"]:
        manifest["guards"][guard]["enabled"] = draw(st.booleans())
    for key in manifest["quality"]:
        manifest["quality"][key] = draw(st.booleans())
    keep = draw(st.lists(st.sampled_from(MCP_NAMES), unique=True, max_size=len(MCP_NAMES)))
    manifest["mcp"] = {name: manifest["mcp"][name] for name in keep}
    for name, server in manifest["mcp"].items():
        server["disabled"] = draw(st.booleans())
        server["auto_approve"] = draw(st.lists(st.sampled_from(["a_read", "b_read", "c_read"]), unique=True, max_size=3))
        server["version"] = draw(st.from_regex(r"\A[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\Z"))
    return manifest
