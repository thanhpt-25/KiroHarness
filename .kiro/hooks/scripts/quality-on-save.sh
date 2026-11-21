#!/bin/sh
# Quality_Hook (PostFileSave): runs scripts/lint.sh on the saved file, and
# scripts/test.sh on it when it is a test file.
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  echo "quality-on-save: python3 not found; skipped"
  exit 0
fi
exec python3 -I "$dir/../../../harness/core/quality.py"
