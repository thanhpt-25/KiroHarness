"""Load the Capability_Matrix and classify native tool IDs (Requirements 4.2, 9.1)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hookio import workspace_root  # noqa: E402

CAPABILITIES_FILE = "harness/capabilities.json"


class CapabilityError(Exception):
    pass


def capabilities_path(root=None) -> Path:
    return Path(root or workspace_root()) / CAPABILITIES_FILE


def load_capabilities(root=None) -> dict:
    path = capabilities_path(root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        raise CapabilityError(f"could not load {path}: {exc}") from None
    if not isinstance(data, dict) or not isinstance(data.get("agents"), dict):
        raise CapabilityError(f"{path}: missing 'agents' object")
    return data


def agent_entry(caps: dict, agent: str) -> dict:
    try:
        return caps["agents"][agent]
    except KeyError:
        raise CapabilityError(f"agent {agent!r} is not in the Capability_Matrix") from None


def classify(entry: dict, tool_id):
    """Return ``(category, mapping)`` for a native tool ID.

    ``mapping`` is the Tool_Map entry (may be empty). Unknown IDs are category
    ``other``, except IDs with a known MCP prefix, which are ``mcp``.
    """
    if not isinstance(tool_id, str):
        return None, {}
    mapping = entry.get("tool_map", {}).get(tool_id)
    if mapping:
        return mapping["category"], mapping
    for prefix, category in entry.get("tool_prefix_map", {}).items():
        if tool_id.startswith(prefix):
            return category, {}
    return "other", {}


def tools_in_category(entry: dict, category: str) -> list:
    return sorted(tool for tool, mapping in entry.get("tool_map", {}).items() if mapping["category"] == category)
