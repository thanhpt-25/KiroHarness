# 0001. `control_bash_process` stop calls are allowed

- Status: Accepted
- Date: 2026-11-21
- Criteria: kiro-agent-harness-template/R4.4

## Context

The Destructive_Command_Guard runs on `PreToolUse` for `execute_bash`,
`execute_pwsh`, and `control_bash_process`. Kiro uses `control_bash_process`
both to start a background command (with a `command` field) and to stop one
(with `action: "stop"` and no command). Read literally, Requirement 4.4 says a
payload without a non-empty command must be blocked, which would make it
impossible for the agent to stop a background process it started.

## Decision

A `control_bash_process` call whose `tool_input.action` is `"stop"` exits 0
without a command. Every other payload without a command still exits 2.
Stopping a process cannot run new code, so allowing it does not widen what the
agent can do.

## Consequences

- Requirement 4.4 is read as "a payload that would run a command must carry
  it". The exception is limited to this one tool and action.
- If Kiro adds other actions to `control_bash_process`, they are blocked until
  this record is revisited.

## Verification

`tests/hooks/test_destructive_guard.py` covers the stop call and the
missing-command block; `.kiro/hooks/scripts/lib/destructive_guard.py` holds the
exception.
