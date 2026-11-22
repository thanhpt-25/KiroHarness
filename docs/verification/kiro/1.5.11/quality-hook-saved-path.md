---
criteria: [agent-harness-platform/R3.4]
agent: kiro
agent_version: 1.5.11
os: macOS (Darwin arm64 27.2.0)
date: 2026-11-21
verdict: partial
---

# Quality hook receives the saved path

Kiro 1.5.11, Kiro Agent 0.66.123. Fill in `verdict` (pass, fail or partial) and `## Observed`.

## Steps

1. Set `LINT_FILE_COMMAND` in `scripts/project-commands.env` to `echo linting` (undo afterwards), then save `src/probe.py`.

Pass means: The hook output names `src/probe.py` and `linting`.

## Observed

With `LINT_FILE_COMMAND="echo linting"` set, `src/probe.py` was saved from the editor with Cmd+S. The person who ran the check reported "đã save nhưng không thấy output" (saved, but saw no output): no hook output was found in Kiro, including in View > Output.

The event does reach the hook. A `PostFileSave` payload was recorded during payload capture (`tests/fixtures/payloads/kiro/1.5.11/PostFileSave/20261121T170925-000.json`), and its `file_path` is `/WORKSPACE/src/probe.py`. Replaying that payload through `.kiro/hooks/scripts/quality-on-save.sh` outside Kiro prints `quality-on-save: passed lint (LINT_FILE_COMMAND) for src/probe.py` and exits 0. That line names the path but not `linting`, because the lint command's own output is not shown when the lint passes. So the pass criterion as written cannot be met even when the hook works.

Verdict is `partial`: the saved path reaches the hook, but Kiro 1.5.11 showed no hook output to the user. Next step: decide where a successful `PostFileSave` hook's output is surfaced (or whether only failures are), and reword the pass criterion to match the hook's real output.

## Notes

Not completed by the agent. The agent set `LINT_FILE_COMMAND="echo linting"` and rewrote `src/probe.py` (unchanged content) with its file-write tool. No hook output appeared, which is inconclusive: a write by the agent may not count as a `PostFileSave` event. The setting was reverted to the placeholder and `src/probe.py` matches its backup. The check was then repeated by hand from the editor (see Observed), and `LINT_FILE_COMMAND` was reverted to the placeholder afterwards.
