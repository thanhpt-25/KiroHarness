# 0006. Agent-neutral core layout and supported agents

- Status: Accepted
- Date: 2026-11-21
- Criteria: agent-harness-platform/R4.1, agent-harness-platform/R4.2, agent-harness-platform/R5.1, agent-harness-platform/R9.1

## Context
Hook runtime and policy lived under `.kiro/hooks/scripts/`, so another agent could not reuse them. Official hook documentation was reachable only for Kiro and Claude Code (code.claude.com, 2026-11-21); Cursor, Copilot, Codex and Gemini docs were unreachable from the build environment.

## Decision
- Runtime modules move to `harness/core/` and shared policy to `harness/policy/`; Kiro wrappers stay in `.kiro/hooks/scripts/` and call the core. No compatibility copies of policy files are kept.
- `harness/capabilities.json` is the single source for per-agent events, tool maps and output contracts. Status is `documented` until a Manual_Check_Record exists.
- Adapters are table-driven from the matrix. Only Kiro and Claude Code are implemented; Cursor, Copilot, Codex and Gemini are listed under `deferred` and need verified docs first.
- Policy `risky-tools.conf` uses `category:<name>`, `<agent>:<tool-id>` or legacy bare Kiro IDs.

## Consequences
Paths in docs and tests changed once. New agents need a matrix entry plus fixtures, not new guard code.

## Verification
`tests/core/`, properties P29-P33 and P44, `tests/validator/test_capabilities_check.py`.
