# Architecture

One neutral tree is the source of truth; every Agent's files are generated from it and committed.

```text
harness/manifest.json + harness/guidance + harness/kiro/hooks + harness/policy
        | scripts/harness sync (pure plan, then write; lock file protects hand edits)
        v
.kiro/*   AGENTS.md   CLAUDE.md + .claude/*   .cursor/rules   .github/copilot-instructions.md

Agent hook -> harness/bin/guard <agent> <trigger> -> Adapter decode -> guards -> combine -> Adapter encode
```

- **Core** (`harness/core/`): Harness_Event, guards, Adapters, Decision_Log. Standard library only. Decisions combine as first deny, then first ask, then allow.
- **Generator** (`scripts/harness_cli/`): renders Agent files from the Manifest; Kiro output is byte-identical to the original template.
- **Validator** (`scripts/harness_validator/`): offline checks for configuration, drift, traceability, links and release gates.
- **Evidence**: tests tagged with `Validates:`, property tests, evals, coverage and mutation gates, and Manual_Check_Records for what needs a real Agent.

Decisions are recorded as ADRs: see the [ADR index](../adr/README.md). The roadmap and requirements are in `.kiro/specs/agent-harness-platform/`.
