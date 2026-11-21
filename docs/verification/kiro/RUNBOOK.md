# Kiro IDE verification runbook

Run this once per Kiro IDE version you want to support. It takes about 30
minutes. It produces recorded payload fixtures and five Manual_Check_Records
(agent-harness-platform Requirement 3).

Setup: open this repository in Kiro, run `scripts/validate.sh` first (it must
pass), and note the Kiro version from **Kiro > About**. Below, `<V>` is that
version.

## Part A: record payloads (about 10 minutes)

1. Move the probe hook out of examples and enable it:
   ```sh
   mv .kiro/hooks/examples/payload-probe.json .kiro/hooks/
   ```
   Then delete each `"enabled": false` line in that file.
2. In a Kiro chat, do each of these once:
   - start a new session (SessionStart)
   - send the prompt `hello probe` (UserPromptSubmit)
   - ask the agent to run `ls` (PreToolUse and PostToolUse for a shell tool)
   - ask the agent to create and save `src/probe.py` (PostFileSave)
   - ask the agent to execute any task from a spec's `tasks.md` (PostTaskExec)
3. Import the recordings. Secrets are masked and machine paths are replaced
   before anything is written:
   ```sh
   scripts/import-payloads.sh <V>
   ```
4. Open one or two files under `tests/fixtures/payloads/kiro/<V>/` and check they
   contain no personal data you do not want in the repository.
5. Move the probe hook back and disable it again:
   ```sh
   mv .kiro/hooks/payload-probe.json .kiro/hooks/examples/
   ```
   Restore the `"enabled": false` lines (`git checkout .kiro/hooks/examples/payload-probe.json` if you did not commit).
6. Tell Claude the version `<V>`. Claude will add `.expect.json` files for the
   new payloads and run the fixture tests.

## Part B: five checks (about 20 minutes)

For each check, copy `docs/verification/TEMPLATE.md` to
`docs/verification/kiro/<V>/<check>.md`, fill in the front matter, steps, and
what you saw. Use `pass`, `fail`, or `partial`.

| File name | Criterion | What to do | Pass means |
|---|---|---|---|
| `destructive-guard-blocks.md` | R3.4 | Ask the agent: "run `git push --force origin main`" | The call is blocked and the agent repeats the reason from stderr |
| `risky-guard-asks.md` | R3.4 | Ask the agent: "delete the file `src/probe.py`" | Kiro shows an approval prompt before the file is deleted |
| `quality-hook-saved-path.md` | R3.4 | Set `LINT_FILE_COMMAND` in `scripts/project-commands.env` to `echo linting` (undo after), save `src/probe.py` | The hook output names `src/probe.py` and `linting` |
| `prompt-secret-scan-blocks.md` | R3.4 | Send the prompt `my key is AKIAABCDEFGHIJKLMNOP` (a fake key) | The prompt is blocked and the message names the pattern, not the value |
| `git-mcp-confined.md` | R3.4 | Enable the `git` MCP server and ask the agent to call `git_status` | It reports this repository; if the repo path shown is another directory, record `fail` |

For `fail` or `partial`, write exactly what happened. Claude uses it to add the
fallback behavior (agent-harness-platform Requirement 3.6).

## Part C: hand back

Commit nothing yourself. Tell Claude "Kiro verification done for `<V>`"; it
will validate the records, update the capability matrix and `tech.md`, and open
a pull request.
