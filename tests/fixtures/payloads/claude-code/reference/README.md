# Claude Code reference payloads

Hand-written from the hook documentation at https://code.claude.com/docs/en/hooks (read 2026-11-21), not recorded from a running Claude Code. They pin the contract the Adapter implements. Recorded payloads from a real Claude Code go in sibling `<claude-version>/` directories (see `docs/verification/claude-code/RUNBOOK.md`); the fixture test picks them up without code changes.

`/WORKSPACE` stands for the workspace root and `/HOME` for the home directory. Each `<name>.expect.json` gives the exit code, optionally `decision` (`ask`) and a `stderr` substring.
