# 0004. Validator hook scope

- Status: Accepted
- Date: 2026-11-21
- Criteria: kiro-agent-harness-template/R10.1

## Context

Requirement 10.1 says the validator checks "every JSON file in
`.kiro/hooks/`". Taken recursively, that would treat any JSON data file a hook
script keeps under `.kiro/hooks/scripts/` as a Hook_File and report schema
errors for it.

## Decision

The validator checks JSON files directly in `.kiro/hooks/` and in
`.kiro/hooks/examples/`. Hook script configuration under
`.kiro/hooks/scripts/` uses non-JSON formats (`.txt`, `.conf`) and is checked
by its own rules (`DESTR-LIST`, `RISKY-LIST`, `RISKY-COVER`).

## Consequences

- Disabled example hooks are validated, so enabling one cannot surprise the
  developer.
- A JSON file added under `.kiro/hooks/scripts/` is not validated as a hook.
  Keep script configuration in non-JSON formats.

## Verification

`scripts/harness_validator/__main__.py` discovery and
`tests/validator/test_validator_main.py`.
