# Architecture Decision Records

Each record explains one decision, the context that forced it, and what it
changes. Records are numbered and never deleted; a replaced decision is marked
`Superseded by NNNN`.

| ADR | Title | Status | Affects |
|---|---|---|---|
| [0001](0001-control-bash-process-stop-calls.md) | `control_bash_process` stop calls are allowed | Accepted | kiro-agent-harness-template/R4.4 |
| [0002](0002-autoapprove-three-tiers.md) | Three-tier `autoApprove` severity | Accepted | kiro-agent-harness-template/R8.9, R10.8 |
| [0003](0003-printer-key-order-for-optional-fields.md) | Printer key order for optional hook fields | Accepted | kiro-agent-harness-template/R9.7 |
| [0004](0004-validator-hook-scope.md) | Validator hook scope | Accepted | kiro-agent-harness-template/R10.1 |
| [0005](0005-git-server-confinement.md) | Git MCP server confinement with `--repository .` | Accepted, pending IDE check | kiro-agent-harness-template/R8.8 |
| [0006](0006-agent-neutral-core-layout.md) | Agent-neutral core layout and supported agents | Accepted | agent-harness-platform/R4.1, R4.2, R5.1, R9.1 |

## Template

```markdown
# NNNN. Title

- Status: Proposed | Accepted | Superseded by NNNN
- Date: YYYY-MM-DD
- Criteria: <spec>/R<n>.<m>, ...

## Context
## Decision
## Consequences
## Verification
```
