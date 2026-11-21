#!/bin/sh
# Lint_Command: lint exactly one file with LINT_FILE_COMMAND from
# scripts/project-commands.env.
# Usage: scripts/lint.sh <file>
# Exit 3 with "not configured: LINT_FILE_COMMAND" when the command is empty
# or still a placeholder; otherwise the linter's exit code.
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 1
key=LINT_FILE_COMMAND
if [ "$#" -ne 1 ]; then
  echo "usage: scripts/lint.sh <file>" >&2
  exit 2
fi
cmd=$(sed -n "s/^$key=\"\(.*\)\"[[:space:]]*\$/\1/p" "$dir/project-commands.env" 2>/dev/null | tail -n 1)
if [ -z "$(printf '%s' "$cmd" | tr -d '[:space:]')" ] ||
  printf '%s' "$cmd" | grep -Eq '\{\{[A-Z][A-Z0-9_]{0,63}\}\}'; then
  echo "not configured: $key"
  exit 3
fi
# The path is a positional argument, so shell metacharacters in it are not run.
exec sh -c "$cmd \"\$1\"" lint "$1"
