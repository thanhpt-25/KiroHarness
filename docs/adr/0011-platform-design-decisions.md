# 0011. Platform design decisions D1 to D8 and the supported-Agent set

- Status: Accepted
- Date: 2026-11-21
- Criteria: agent-harness-platform/R16.2, agent-harness-platform/R1.3, agent-harness-platform/R4.1, agent-harness-platform/R6.1, agent-harness-platform/R9.1, agent-harness-platform/R15.2, agent-harness-platform/R14.1

## Context
The decision table in `.kiro/specs/agent-harness-platform/design.md` is the source of each decision. This record states each one with its consequence and where it is implemented, so the reasoning survives the spec being edited.

## Decisions
| ID | Decision | Consequence | Implemented in |
|---|---|---|---|
| D1 | `harness/` is the source of truth; every Agent file, including `.kiro/`, is a committed Generated_File. | Diff noise in generated files; the drift check keeps them honest. | ADR 0007, `scripts/harness sync` |
| D2 | Guard logic lives in `harness/core/`; `.kiro/hooks/scripts/*.sh` are thin wrappers. | One implementation for every Agent. | ADR 0006 |
| D3 | Runtime is Python 3.10+ standard library and POSIX `sh`; Hypothesis, coverage and mutation tools are dev-only and pinned. | No install step for adopters; more hand-written render code. | `requirements-dev.txt`, `requirements-mutation.txt` |
| D4 | `harness/guidance/*.md` with Kiro-compatible front matter is the canonical guidance format. | Kiro's inclusion modes map to other Agents with the least loss. | ADR 0007 |
| D5 | Defense in depth: hooks, native permission rules and guidance, per guard, as each Agent allows. | The matrix records which layers each Agent has. | ADR 0008 |
| D6 | The destructive guard stays pattern-based, is measured with a Bypass_Corpus, and the gaps are documented. | Honest limits; sandboxing is recommended for untrusted work. | ADR 0009, `evals/` |
| D7 | Traceability uses `Validates:` tags plus Manual_Check_Records, collected by `scripts/harness trace`. | Light, greppable; the validator checks both directions. | ADR 0009 |
| D8 | `harness/capabilities.json` is a dated, machine-readable capability matrix. | Claims about an Agent become checkable and can go stale visibly. | ADR 0006, `capabilities_check.py` |

## Supported Agents (Task 7 decision)
Kiro and Claude Code have hook adapters. Cursor and Copilot are guidance-only (`"hooks": false`). Codex and Gemini are deferred. Their formats are documented but unverified until the manual checks run; the matrix status says so.

## Verification
`tests/validator/test_docs_reference.py`, `tests/validator/test_docs_index.py`.
