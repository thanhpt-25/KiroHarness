# Git Hook Implementation Best Practices

This guide describes how to add local Git hooks to a project using this harness. Git hooks are separate from Kiro hooks: Git invokes them during Git operations such as commit and push, while Kiro hooks run on IDE events and tool calls.

The repository includes executable pre-commit, commit-msg, and pre-push hooks in .githooks/, plus an opt-in installer at scripts/install-git-hooks.sh. Installation updates only this repository's local Git configuration; it does not alter a contributor's global configuration.

## Recommended design

- Keep hook scripts in the repository, for example in .githooks/, so the team can review and version them.
- Select that directory with the repository-local core.hooksPath setting. This changes local Git configuration and does not modify a contributor's global Git setup.
- Make hooks small, executable, and fast. Put substantive checks in normal project scripts and have hooks call those scripts.
- Run checks that are deterministic and available offline. Do not fetch packages, deploy, rewrite history, or mutate the index unexpectedly from a hook.
- Fail with a clear message and non-zero status when a required check fails. Do not hide a command's failure behind a pipeline or unconditional success.
- Treat hooks as a developer feedback aid, not as a security boundary. CI and protected-branch policies must enforce checks that cannot be bypassed.
- Avoid modifying staged files from hooks. If a formatter changes a file, ask the developer to review and stage the resulting diff, or use a staged-file tool that safely updates only selected paths.
- Account for partial staging. Whole-file formatters or tests may inspect unstaged changes; document that behavior and avoid silently committing content the developer did not stage.
- Use POSIX sh for portable examples, quote paths and arguments, and resolve the repository root rather than assuming the caller's current directory.
- Provide an explicit bypass route for emergencies, consistent with team policy. Git supports SKIP-like conventions only when implemented by the hook; the standard bypass is git -c core.hooksPath=/dev/null commit or the --no-verify option for hooks that honor it. Do not treat a bypass as approval for unsafe operations.

## Enable repository-managed hooks

From the repository root, opt in to the repository-managed hook:

```sh
scripts/install-git-hooks.sh
```

The installer sets core.hooksPath to .githooks in local Git configuration. The setting is not shared by cloning. Inspect the installer before opting in. It replaces any previously configured local core.hooksPath value; review that setting first if you already use another hook manager. Do not run the installer from a general setup script without an explicit opt-in.

Inspect the effective setting with:

```sh
git config --show-origin --get core.hooksPath
```

Git does not copy hooks from .git/hooks when core.hooksPath points elsewhere. Keep one managed hook directory and avoid overlapping installation methods such as Husky plus a custom core.hooksPath unless their interaction is deliberate.

## Implemented pre-commit hook

The committed implementation is [.githooks/pre-commit](../.githooks/pre-commit). It resolves the repository root, checks that python3 is available, and runs the offline validation command:

```sh
#!/bin/sh
set -u

if ! root=$(git rev-parse --show-toplevel 2>/dev/null); then
  echo "pre-commit: cannot locate the Git repository root" >&2
  exit 2
fi

cd "$root" || exit 2

if ! command -v python3 >/dev/null 2>&1; then
  echo "pre-commit: python3 is required; install Python 3.10 or newer" >&2
  exit 2
fi

echo "pre-commit: running harness validation and unit tests"
if ! sh scripts/validate.sh; then
  echo "pre-commit: checks failed; fix the errors and commit again" >&2
  exit 1
fi
```

This hook runs the full configuration validator and hook/validator unit suites. It does not run Hypothesis properties or networked MCP integration tests. If this is too slow for every commit, split fast checks from the full validation command and keep the full suite in CI; do not weaken CI to make the local hook faster.

The hook validates the working tree, not only the staged snapshot. For projects that allow partial staging, either accept and document this stricter behavior or build a staged-file-aware check with temporary index/worktree handling. Do not reset or restage files automatically.

## Commit-message hook

A commit-message hook is useful when a repository has a simple, agreed message format. This repository's [.githooks/commit-msg](../.githooks/commit-msg) enforces a non-blank first line, a maximum of 72 characters, and no trailing whitespace. It does not require Conventional Commits or an issue identifier.

The 72-character limit is a repository convention and can be adjusted if the team adopts a different commit format.

## Pre-push hook

[.githooks/pre-push](../.githooks/pre-push) runs the Hypothesis property suite with the default profile. It uses already-installed dependencies only; it does not download packages or start MCP servers. If Hypothesis is unavailable, the push is stopped with instructions to install requirements-dev.txt first. The full profile suite takes longer than pre-commit checks, so it runs before pushing rather than on every commit.

To run the same property suite manually with dependency installation enabled when needed:

```sh
scripts/test-properties.sh
```

## Hook behavior and safety

### Exit codes and output

Use exit code 0 for success, non-zero for a rejected action, and stderr for actionable errors. Include the command or rule that failed and a concise next step. Avoid printing environment values, tokens, or full secret-bearing configuration.

### Runtime and dependencies

Prefer existing project commands and standard tools. If a hook needs Python, Node, or another runtime, check for it and explain how to install it. Do not make a Git hook depend on an implicit network download; developers should be able to understand and control dependency installation.

### Scope and performance

Run only the checks needed for the hook's purpose. The pre-commit hook runs validation and unit tests; the pre-push hook runs property tests. Keep external-service integration checks out of automatic hooks. Use timeouts for commands that can hang.

### Avoid risky side effects

Hooks should not deploy, publish, push, delete broad paths, rewrite commits, or change Git configuration. If a task truly needs a side effect, keep it in an explicit command that the developer runs knowingly.

### Keep enforcement in CI

Hooks can be skipped, may not be installed, and can differ across operating systems. Enforce required formatting, tests, and security policy in CI. Use branch protection or server-side controls for rules that must not be bypassed.

## Troubleshooting

Check that the hook file is executable and that Git is using the expected directory:

```sh
git config --show-origin --get core.hooksPath
ls -l .githooks
```

Run the hook directly from the repository root to see its output. Git hook scripts receive arguments documented for their hook type; for example, commit-msg receives the path to the proposed message file. Do not assume the script starts in the repository root; resolve it through git rev-parse --show-toplevel.

To skip a hook for a permitted emergency, use the team's documented bypass policy. Common Git options include --no-verify for pre-commit and commit-msg. A bypass should be visible in the review process and must not replace required CI checks.
