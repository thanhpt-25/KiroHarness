# 0002. Three-tier `autoApprove` severity

- Status: Accepted
- Date: 2026-11-21
- Criteria: kiro-agent-harness-template/R8.9, kiro-agent-harness-template/R10.8

## Context

Requirement 8.9 says a non-read-only tool in `autoApprove` is an error.
Requirement 10.8 says a tool that is not on the read-only allowlist is a
warning. The two disagree for tools the validator has never seen: it cannot
know whether an unknown tool is read-only.

## Decision

The validator sorts each `autoApprove` entry into one of three tiers:

| Tier | Rule | Severity |
|---|---|---|
| On `read_only_allowlist` in `scripts/validator-config.json` | allowed | none |
| On `known_mutating_tools`, or the name contains a mutating verb | `MCP-AUTOAPPROVE` | error |
| Anything else | `MCP-AUTOAPPROVE-UNKNOWN` | warning |

## Consequences

- Known-dangerous auto-approval always fails validation (Requirement 8.9).
- New tools surface as warnings instead of blocking adopters (Requirement 10.8).
- Maintainers keep the two lists in `validator-config.json` current. The
  platform spec (agent-harness-platform/R10.4) later replaces the guesswork with
  per-server tool inventories.

## Verification

`scripts/harness_validator/mcp.py` implements the tiers; Property 22
(`tests/property/test_p22_autoapprove.py`) checks the classification.
