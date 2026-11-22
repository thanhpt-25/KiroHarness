---
criteria: [agent-harness-platform/R3.4]
agent: kiro
agent_version: 1.5.11
os: macOS (Darwin arm64 27.2.0)
date: 2026-11-21
verdict: pass
---

# Git MCP server is confined to this repository

Kiro 1.5.11, Kiro Agent 0.66.123. Fill in `verdict` (pass, fail or partial) and `## Observed`.

## Steps

1. Enable the `git` MCP server and ask the agent to call `git_status`.

Pass means: It reports this repository. If the repo path shown is another directory, record `fail`.

## Observed

The `git` MCP server is configured with `--repository .`. The agent called `git_status` with `repo_path: "."`. It reported branch `main`, up to date with `origin/main`, and the untracked paths `docs/verification/kiro/1.5.11/`, `src/` and `tests/fixtures/payloads/kiro/1.5.11/`. These match `git status` run directly in `<repo>`, so the server reports this repository. The call ran without an approval prompt because `git_status` is on the server's `autoApprove` list. Not tested: a `repo_path` outside this repository.


## Notes
