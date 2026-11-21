"""Replay neutral scenarios through every hook-capable Agent's real guard wrapper.

Scenario: {id, description, trigger, category, input, expect: deny|ask|allow}. For each Agent in
harness/capabilities.json with hooks, the native payload is built from the Agent's tool_map (the first
tool of the scenario's category). Agents with no tool for a category are reported as "n/a".
Usage: python3 evals/run.py [--agent NAME] [--json]  (exit 1 on any mismatch). Stdlib only.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENT = {"kiro": {"pre_tool": "PreToolUse", "prompt_submit": "UserPromptSubmit"},
         "claude-code": {"pre_tool": "PreToolUse", "prompt_submit": "UserPromptSubmit"}}
INPUT_KEY = {"shell": "command", "web": "url"}


def agents(only=None):
    caps = json.loads((ROOT / "harness" / "capabilities.json").read_text())["agents"]
    return {name: spec for name, spec in caps.items() if spec.get("hooks") and (not only or name == only)}


def scenarios():
    return [json.loads(p.read_text()) for p in sorted((ROOT / "evals" / "scenarios").glob("*.json"))]


def native_payload(agent, spec, scenario):
    """Return the native JSON payload, or None when the Agent has no tool for the category."""
    event = EVENT[agent][scenario["trigger"]]
    base = {"session_id": "eval", "hook_event_name": event, "cwd": str(ROOT)}
    if scenario["trigger"] == "prompt_submit":
        return {**base, "prompt": scenario["input"]}
    for tool, mapping in spec["tool_map"].items():
        if mapping["category"] == scenario["category"]:
            if "command" in mapping or "url" in mapping:
                field = mapping.get("command") or mapping.get("url")
                return {**base, "tool_name": tool, "tool_input": {field: scenario["input"]}}
            return {**base, "tool_name": tool, "tool_input": {mapping["paths"][0]: scenario["input"]}}
    return None


def outcome(agent, trigger, payload):
    env = {**os.environ, "HARNESS_DECISION_LOG": "0"}
    result = subprocess.run([str(ROOT / "harness" / "bin" / "guard"), agent, trigger],
                            input=json.dumps(payload).encode(), capture_output=True, cwd=ROOT, env=env, timeout=30)
    if result.returncode == 2:
        return "deny"
    out = result.stdout.decode().strip()
    if result.returncode == 0 and out:
        return json.loads(out)["hookSpecificOutput"]["permissionDecision"]
    return "allow" if result.returncode == 0 else f"error:{result.returncode}"


def replay(only=None):
    rows = []
    for agent, spec in agents(only).items():
        for scenario in scenarios():
            payload = native_payload(agent, spec, scenario)
            actual = "n/a" if payload is None else outcome(agent, scenario["trigger"], payload)
            rows.append({"agent": agent, "id": scenario["id"], "expect": scenario["expect"], "actual": actual,
                         "ok": actual in ("n/a", scenario["expect"])})
    return rows


def corpus_rows():
    """Replay evals/bypass-corpus.json through every hook-capable Agent's shell tool.

    must-block: must give the recorded deny/ask. known-gap: documented bypass, must still be
    allowed; when a gap closes the row fails so the corpus is promoted to must-block.
    safe: must be allowed. A change in either direction is reported.
    """
    items = json.loads((ROOT / "evals" / "bypass-corpus.json").read_text())
    rows = []
    for agent, spec in agents().items():
        tool = next((t for t, m in spec["tool_map"].items() if m["category"] == "shell"), None)
        if tool is None:
            continue
        for item in items:
            payload = {"session_id": "eval", "hook_event_name": "PreToolUse", "cwd": str(ROOT),
                       "tool_name": tool, "tool_input": {"command": item["command"]}}
            actual = outcome(agent, "pre_tool", payload)
            rows.append({"agent": agent, "id": item["id"], "class": item["class"], "expect": item["expect"],
                         "actual": actual, "ok": actual == item["expect"]})
    return rows


def main(argv) -> int:
    if "--corpus" in argv:
        rows = corpus_rows()
        bad = [r for r in rows if not r["ok"]]
        for r in bad:
            print(f"CHANGED {r['agent']}/{r['id']} ({r['class']}): expected {r['expect']}, got {r['actual']}")
        gaps = sum(r["class"] == "known-gap" for r in rows)
        print(f"bypass corpus: {len(rows)} replayed, {gaps} known gaps, {len(bad)} changed")
        return 1 if bad else 0
    only = argv[argv.index("--agent") + 1] if "--agent" in argv else None
    rows = replay(only)
    bad = [r for r in rows if not r["ok"]]
    if "--json" in argv:
        print(json.dumps(rows, indent=1))
    for r in bad:
        print(f"MISMATCH {r['agent']}/{r['id']}: expected {r['expect']}, got {r['actual']}")
    ran = sum(r["actual"] != "n/a" for r in rows)
    print(f"evals: {ran} replayed, {len(rows) - ran} n/a, {len(bad)} mismatched")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
