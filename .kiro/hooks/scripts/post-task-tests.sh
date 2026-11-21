#!/bin/sh
# PostTaskExec hook: runs scripts/test.sh once. Exit 0 on pass or when
# TEST_COMMAND is not configured, exit 2 when tests fail or time out.
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 2
if ! command -v python3 >/dev/null 2>&1; then
  echo "post-task-tests: python3 not found" >&2
  exit 2
fi
exec python3 -I "$dir/lib/post_task.py"
