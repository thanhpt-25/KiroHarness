# 0007. Generator design and Kiro byte-equivalence

- Status: Accepted
- Date: 2026-11-21
- Criteria: agent-harness-platform/R6.1, agent-harness-platform/R6.3, agent-harness-platform/R6.5, agent-harness-platform/R6.8, agent-harness-platform/R7.1, agent-harness-platform/R7.2

## Context
Agents read files from fixed paths, so generated output must stay committed. A Kiro-only adopter must see no change.

## Decision
- Sources: `harness/manifest.json`, `harness/guidance/*.md` (steering with Kiro-style front matter), `harness/kiro/hooks/*.json`. The Generator is pure (`plan.build_plan`) and uses only the standard library.
- Kiro outputs carry no header: steering is copied verbatim, hooks are printed by the existing Hook_Config_Printer, and `mcp.json` by a deterministic printer. Provenance for them is the SHA-256 lock in `harness/generated.lock.json`. This is the "no comments" path of Requirement 6.5 applied to Markdown too, chosen so Kiro files stay byte-identical to the pre-migration baseline (Property 35). One content change is documented: the `Untrusted Tool Output` section in the security source (Requirement 7.5).
- Other agents' Markdown outputs start with an HTML-comment header naming sources and the harness version.
- `sync` refuses to overwrite a file whose hash differs from the lock (or that exists without a lock entry) unless `--force`; `--check` writes nothing.
- Claude Code gets `AGENTS.md` plus `CLAUDE.md` (`@AGENTS.md` import) and `.claude/rules` for path-scoped guidance. `auto` falls back to an always-loaded rule with a warning, per the Capability_Matrix.
- Cursor and Copilot renderers follow the mapping in the design but their formats were not verifiable (docs unreachable); `sync` warns until a Manual_Check_Record exists. Patterns are brace-expanded for targets without brace support.

## Consequences
Editing a generated file is an error until the source is changed. Test fixtures that edit generated files in place must expect DRIFT.

## Verification
`tests/generator/`, properties P34 to P37.
