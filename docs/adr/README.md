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
| [0007](0007-generator-design.md) | Generator design and Kiro byte-equivalence | Accepted | agent-harness-platform/R6.1, R6.3, R6.5, R6.8, R7.1, R7.2 |
| [0008](0008-claude-code-adapter-and-mcp-inventory.md) | Claude Code adapter, derived permissions and MCP inventories | Accepted, pending verification | agent-harness-platform/R8.1, R8.2, R8.3, R9.3, R9.4, R10.2, R10.4 |
| [0009](0009-protection-traceability-and-evals.md) | Protected paths, Decision_Log, traceability and evals | Accepted | agent-harness-platform/R11.1, R12.1, R13.1, R14.1-R14.4, R15.1-R15.3 |
| [0010](0010-versioning-policy.md) | Versioning policy | Accepted | agent-harness-platform/R17.1, R16.5 |
| [0011](0011-platform-design-decisions.md) | Platform design decisions D1 to D8 and the supported-Agent set | Accepted | agent-harness-platform/R16.2 |

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
