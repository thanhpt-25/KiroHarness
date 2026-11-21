---
inclusion: always
---

# Project Structure

## Application code

- Source code lives in `{{SOURCE_DIR}}`.
- Tests live in `{{TEST_DIR}}`.

Put new modules next to related code. Ask before creating a new top-level
directory.

## Agent harness

- `.kiro/steering/`: project context for the agent (these files).
- `.kiro/hooks/`: hook files; `.kiro/hooks/scripts/` holds the scripts they run
  and the guard lists; `.kiro/hooks/examples/` holds disabled example hooks.
- `.kiro/settings/mcp.json`: workspace MCP servers.
- `.kiro/specs/`: feature specs (requirements, design, tasks).
- `scripts/`: lint, test, and validation commands.
- `docs/CUSTOMIZING.md`: how to change each part of the harness.

Run `scripts/validate.sh` after changing anything under `.kiro/` or `scripts/`.
