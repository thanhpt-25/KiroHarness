---
inclusion: always
---

# Technology

## Project stack

- Primary language: {{PRIMARY_LANGUAGE}}
- Package manager: {{PACKAGE_MANAGER}}
- Lint, file test, and full test commands: set in `scripts/project-commands.env`.

Use the package manager above for every dependency change. Do not add a
dependency without saying why it is needed.

## Harness runtime

The agent harness in this repository (hooks, the Config_Validator, and
`scripts/validate.sh`) needs:

- Python 3.10 or newer, standard library only. Hypothesis is a dev-only
  dependency used by `scripts/test-properties.sh` and is pinned in
  `requirements-dev.txt`.
- A POSIX `sh` for the Hook_Scripts in `.kiro/hooks/scripts/` and the
  scripts in `scripts/`.
- `uv` (`uvx`) to start the MCP servers in `.kiro/settings/mcp.json`.
- Minimum supported Kiro IDE version: 1.1.14. Exit-code blocking for
  `PreToolUse` hooks was measured on this version.
- Verified on Kiro IDE 1.5.11 (Kiro Agent 0.66.123) on 2026-11-21. The
  records are in `docs/verification/kiro/1.5.11/`.

## MCP server pins

MCP server packages are pinned to exact versions in `.kiro/settings/mcp.json`.
The pins were last checked against PyPI on 2026-11-21:

- `awslabs.aws-documentation-mcp-server` 1.2.6
- `mcp-server-fetch` 2026.11.18
- `mcp-server-git` 2026.11.18 (must stay at or above 2026.10.28)

Run `scripts/check-mcp-updates.sh` to compare the pins with PyPI.
