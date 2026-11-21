#!/bin/sh
# Opt in to the repository-managed Git hooks using local Git configuration.
set -u

if ! root=$(git rev-parse --show-toplevel 2>/dev/null); then
  echo "install-git-hooks: run this command inside a Git repository" >&2
  exit 2
fi

hooks_dir="$root/.githooks"
for hook in pre-commit commit-msg pre-push; do
  if [ ! -x "$hooks_dir/$hook" ]; then
    echo "install-git-hooks: missing executable hook: $hooks_dir/$hook" >&2
    exit 2
  fi
done

if ! git -C "$root" config --local core.hooksPath .githooks; then
  echo "install-git-hooks: could not set repository-local core.hooksPath" >&2
  exit 2
fi

echo "Git hooks enabled for this repository (core.hooksPath=.githooks)."
echo "This repository-local setting does not change your global Git configuration."
