# 0008. Claude Code adapter, derived permissions and MCP inventories

- Status: Accepted, pending Claude Code verification
- Date: 2026-11-21
- Criteria: agent-harness-platform/R8.1, agent-harness-platform/R8.2, agent-harness-platform/R8.3, agent-harness-platform/R9.3, agent-harness-platform/R9.4, agent-harness-platform/R10.2, agent-harness-platform/R10.4

## Context
Claude Code runs hooks and has its own permission rules and `.mcp.json`. A nested Claude Code session could not be run from the build sandbox (denied by its permission classifier), so no payload was recorded.

## Decision
- `.claude/settings.json` is fully generated; user overrides go in `.claude/settings.local.json`. One combined guard command per trigger, narrowed with `--only` when the Manifest disables a guard.
- Permission rules are derived only from entries with a static form (literal command prefixes, exact tool names). Others are reported by `sync`, never silently dropped. Rules use the documented `Tool(prefix *)` form; this exact spelling is unverified until the manual checks run.
- Fixtures under `tests/fixtures/payloads/claude-code/reference/` are written from the documentation; recorded ones go in version directories. The matrix status stays `documented`.
- This repository keeps `claude-code` disabled in its own Manifest because its hand-written CLAUDE.md maintainer guide would exceed the context budget once combined with AGENTS.md. Adopters enable it.
- Cursor and Copilot have matrix entries with `"hooks": false` and protection `guidance-only`; codex and gemini stay deferred. `docs/reference/capabilities.md` is generated from the matrix.
- MCP inventories are opt-in files generated from live servers; the validator checks them only when present, so the shipped state has no warnings.

## Consequences
The permission layer is weaker than the hook for rewritten commands (prefix match). Quality hooks `on_save` and `post_task` are not rendered for Claude Code.

## Verification
`tests/core/test_claude_fixtures.py`, `tests/generator/test_claude_native.py`, `tests/generator/test_mcp_inventory.py`, `tests/validator/test_check_mcp_updates.py`.
