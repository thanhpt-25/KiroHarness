#!/bin/sh
# Example PreCompact hook (disabled by default, see .kiro/hooks/examples/).
# Prints a short git snapshot so the summary kept after compaction still
# names the branch, the last commit, and the changed files. Always exits 0.
if ! command -v git >/dev/null 2>&1 || ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "pre-compact-snapshot: git information unavailable"
  exit 0
fi
echo "pre-compact-snapshot: branch $(git symbolic-ref --short -q HEAD || git rev-parse --short HEAD 2>/dev/null)"
echo "pre-compact-snapshot: last commit $(git log -1 --oneline 2>/dev/null || echo none)"
echo "pre-compact-snapshot: changed files:"
git status --short --untracked-files=all 2>/dev/null | head -n 50
exit 0
