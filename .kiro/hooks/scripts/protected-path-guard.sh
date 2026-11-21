#!/bin/sh
# Protected_Path_Guard (PreToolUse). Denies reads, writes and deletes of paths on
# harness/policy/protected-paths.txt, and shell commands that read them (exit 2).
# Fails closed when python3 is missing.
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || {
  echo "protected-path-guard: cannot locate hook scripts; blocking" >&2
  exit 2
}
exec "$dir/../../../harness/bin/guard" kiro pre_tool --only protected-path-guard
