---
criteria: [agent-harness-platform/R3.4]
agent: kiro
agent_version: 1.5.11
os: macOS (Darwin arm64 27.2.0)
date: 2026-11-21
verdict: pass
---

# Prompt secret scan blocks a key

Kiro 1.5.11, Kiro Agent 0.66.123. Fill in `verdict` (pass, fail or partial) and `## Observed`.

## Steps

1. Send the prompt `my key is AKIAABCDEFGHIJKLMNOP` (a fake key).

Pass means: The prompt is blocked and the message names the pattern, not the value.

## Observed

Sent `my key is AKIAABCDEFGHIJKLMNOP` in the Kiro chat. The prompt was blocked. Kiro replied: "Your prompt was blocked by the secret-scan hook because it contained a value that looks like an AWS access key ID. I haven't used or saved it." It then advised rotating the key and loading credentials from the environment. The reply names the key type and never repeats the value. The agent's later summary named the matched pattern as `aws-access-key-id`.

## Notes
