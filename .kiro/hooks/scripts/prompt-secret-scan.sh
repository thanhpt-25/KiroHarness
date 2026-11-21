#!/bin/sh
# UserPromptSubmit hook: blocks prompts containing a value that matches a
# secret pattern from scripts/validator-config.json (exit 2).
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || {
  echo "prompt-secret-scan: cannot locate hook scripts; blocking" >&2
  exit 2
}
if ! command -v python3 >/dev/null 2>&1; then
  echo "prompt-secret-scan: python3 not found; blocking" >&2
  exit 2
fi
exec "$dir/../../../harness/bin/guard" kiro prompt_submit --only prompt-secret-scan
