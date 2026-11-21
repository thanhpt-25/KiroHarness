# 0009. Protected paths, Decision_Log, traceability and evals

- Status: Accepted
- Date: 2026-11-21
- Criteria: agent-harness-platform/R11.1, agent-harness-platform/R11.2, agent-harness-platform/R12.1, agent-harness-platform/R13.1, agent-harness-platform/R14.1, agent-harness-platform/R14.2, agent-harness-platform/R14.3, agent-harness-platform/R14.4, agent-harness-platform/R15.1, agent-harness-platform/R15.2, agent-harness-platform/R15.3

## Context
Phases 2 to 4 gave the Harness one guard core for several Agents. The remaining claims ("secure", "spec-driven", "well tested") were not yet measured.

## Decision
- **Protected paths** are a fourth guard that fails closed. Patterns live in `harness/policy/protected-paths.txt` (`!` re-includes). It covers read, write and delete tools and shell commands that read a protected file.
- **Decision_Log** is `.harness/decisions.jsonl` (git-ignored, masked, rotated at 5 MB with 3 files). A logging failure never changes a Decision. `HARNESS_DECISION_LOG=0` turns it off; the test support code sets it for tests.
- **Traceability** is a `# Validates: <spec>/R<n>.<m>` tag per test file plus Manual_Check_Records. `scripts/harness trace` prints the report and writes `build/traceability.json`; the validator errors on an uncovered criterion in the two required specs and on a tag that names no criterion. Criteria that need Neo's hands or a real Agent are listed in `docs/verification/backlog.txt`; the file may only shrink, and a covered entry is reported so it gets removed.
- **Coverage gate**: `scripts/coverage.sh` runs all tests (unit, property) under coverage 7.10.7 with subprocess patching, because the guards run as `python3 -I` children. Line 90 percent and branch 80 percent on `scripts/harness_validator`, `scripts/harness_cli` and `harness/core`.
- **Mutation testing**: weekly job, `scripts/mutation.sh`, mutmut 2.5.1, 85 percent per guard module. It is not part of `validate.sh` because it takes long.
- **Evals**: neutral scenarios in `evals/scenarios/` are turned into native payloads from the capability matrix and replayed through the real `harness/bin/guard` for every hook-capable Agent. The Bypass_Corpus in `evals/bypass-corpus.json` labels each obfuscated command `must-block`, `known-gap` or `safe`. A change in either direction fails the run, so a closed gap must be promoted on purpose.

## Consequences
The guards are a pattern-based safety net, not a sandbox. The corpus documents what slips through (quote splitting, backslash escapes, encoded pipelines, other interpreters, `find -delete`, glob-built secret paths, `mkfs.*`, `dd if=… of=/dev/…`). Recommend OS-level isolation for untrusted workloads.

## Verification
`tests/evals/test_evals.py`, `tests/validator/test_trace_check.py`, `tests/property/test_p42_traceability.py`, `tests/validator/test_property_convention.py`.
