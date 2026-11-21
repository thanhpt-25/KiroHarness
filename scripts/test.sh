#!/bin/sh
# Test_Command: run tests once (single-run mode) with the commands from
# scripts/project-commands.env.
# Usage: scripts/test.sh          run TEST_COMMAND (the whole suite)
#        scripts/test.sh <file>   run TEST_FILE_COMMAND for one test file
# Exit 3 with "not configured: <KEY>" when the command is empty or still a
# placeholder; otherwise the test runner's exit code.
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 1
if [ "$#" -gt 1 ]; then
  echo "usage: scripts/test.sh [<file>]" >&2
  exit 2
fi
if [ "$#" -eq 1 ]; then key=TEST_FILE_COMMAND; else key=TEST_COMMAND; fi
cmd=$(sed -n "s/^$key=\"\(.*\)\"[[:space:]]*\$/\1/p" "$dir/project-commands.env" 2>/dev/null | tail -n 1)
if [ -z "$(printf '%s' "$cmd" | tr -d '[:space:]')" ] ||
  printf '%s' "$cmd" | grep -Eq '\{\{[A-Z][A-Z0-9_]{0,63}\}\}'; then
  echo "not configured: $key"
  exit 3
fi
# Ask common runners (Vitest, Jest) to run once instead of watching.
CI=true
export CI
if [ "$#" -eq 1 ]; then
  # The path is a positional argument, so shell metacharacters in it are not run.
  exec sh -c "$cmd \"\$1\"" test "$1"
fi
exec sh -c "$cmd"
