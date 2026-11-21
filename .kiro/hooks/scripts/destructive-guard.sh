#!/bin/sh
# Destructive_Command_Guard (PreToolUse). Blocks commands on
# destructive-commands.txt with exit 2. Fails closed when python3 is missing.
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || {
  echo "destructive-command-guard: cannot locate hook scripts; blocking" >&2
  exit 2
}
if ! command -v python3 >/dev/null 2>&1; then
  echo "destructive-command-guard: python3 not found; blocking" >&2
  exit 2
fi
exec python3 -I "$dir/../../../harness/core/destructive_guard.py"
