#!/bin/sh
# SessionStart hook: prints the git branch and the uncommitted file count.
# Always exits 0.
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || {
  echo "Git information unavailable: cannot locate hook scripts"
  exit 0
}
if ! command -v python3 >/dev/null 2>&1; then
  echo "Git information unavailable: python3 not found"
  exit 0
fi
python3 -I "$dir/lib/session_info.py" || echo "Git information unavailable: session_info.py failed"
exit 0
