#!/bin/sh
# Risky_Tool_Guard (PreToolUse). Prints a permissionDecision of "ask" for tool
# calls on risky-tools.conf. Always exits 0; asks when python3 is missing.
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || {
  printf '%s\n' '{"hookSpecificOutput":{"permissionDecision":"ask","permissionDecisionReason":"risky-tool-guard config problem: cannot locate hook scripts"}}'
  exit 0
}
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' '{"hookSpecificOutput":{"permissionDecision":"ask","permissionDecisionReason":"risky-tool-guard config problem: python3 not found"}}'
  echo "risky-tool-guard: python3 not found" >&2
  exit 0
fi
exec "$dir/../../../harness/bin/guard" kiro pre_tool --only risky-tool-guard
