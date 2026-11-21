# 0003. Printer key order for optional hook fields

- Status: Accepted
- Date: 2026-11-21
- Criteria: kiro-agent-harness-template/R9.7

## Context

Requirement 9.7 fixes the key order `name`, `trigger`, `matcher`, `action` for
each Hook_Definition, but Kiro hook files also carry `timeout`, `description`,
`enabled`, and sometimes keys the Template does not know. The printer must
place them somewhere, deterministically, or idempotence (Requirement 9.9)
fails.

## Decision

After the four keys from Requirement 9.7, the printer writes `timeout`,
`description`, and `enabled` (each only when present), then any other keys in
sorted order. Inside `action` it writes `type`, `command`, `prompt`, then other
keys sorted.

## Consequences

- Requirement 9.7 holds for the keys it names; the extra keys only follow them.
- Unknown keys survive a round trip instead of being dropped.

## Verification

Properties 1 to 3 (`tests/property/test_p01_*`, `test_p02_*`, `test_p03_*`)
cover round trip, idempotence, and key order.
