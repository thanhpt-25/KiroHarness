#!/bin/sh
# Destructive_Command_Guard (PreToolUse). Blocks commands on
# harness/policy/destructive-commands.txt with exit 2. Fails closed when python3
# is missing (harness/bin/guard blocks in that case).
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || {
  echo "destructive-command-guard: cannot locate hook scripts; blocking" >&2
  exit 2
}
exec "$dir/../../../harness/bin/guard" kiro pre_tool --only destructive-command-guard
