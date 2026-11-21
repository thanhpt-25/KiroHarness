# Claude Code verification runbook

Run this once per Claude Code version you want to support (about 30 minutes). It
produces recorded payload fixtures and five Manual_Check_Records
(agent-harness-platform Requirement 8.5). Claude cannot run a nested Claude Code
session from its own sandbox, so this part needs your machine.

Setup: in the Manifest set `"claude-code": {"enabled": true}`, run
`scripts/harness sync`, then `scripts/validate.sh` (it must pass). Start
`claude` in the repository and approve the project hooks when prompted. Note the
version from `claude --version`; below, `<V>` is that version.

## Part A: record payloads

1. Create `.claude/settings.local.json` (git-ignored) with a probe on each event:
   ```json
   {"hooks": {
     "SessionStart":     [{"hooks": [{"type": "command", "command": "python3 -I \"$CLAUDE_PROJECT_DIR\"/harness/core/payload_probe.py SessionStart"}]}],
     "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "python3 -I \"$CLAUDE_PROJECT_DIR\"/harness/core/payload_probe.py UserPromptSubmit"}]}],
     "PreToolUse":       [{"matcher": "*", "hooks": [{"type": "command", "command": "python3 -I \"$CLAUDE_PROJECT_DIR\"/harness/core/payload_probe.py PreToolUse"}]}],
     "Stop":             [{"hooks": [{"type": "command", "command": "python3 -I \"$CLAUDE_PROJECT_DIR\"/harness/core/payload_probe.py Stop"}]}]
   }}
   ```
2. In a Claude Code session: send `hello probe`, ask it to run `ls`, to create `src/probe.py`, to read `README.md`, to fetch `https://example.com`, and to call the `git_status` MCP tool.
3. Import (secrets are masked, paths replaced):
   ```sh
   scripts/import-payloads.sh <V> claude-code
   ```
4. Check a file or two under `tests/fixtures/payloads/claude-code/<V>/`, then delete `.claude/settings.local.json`.
5. Tell Claude the version `<V>`; it adds `.expect.json` files and runs the fixture tests.

## Part B: five checks

Copy `docs/verification/TEMPLATE.md` to `docs/verification/claude-code/<V>/<check>.md` per check and fill it in (`pass`, `fail`, `partial`).

| File name | Criterion | What to do | Pass means |
|---|---|---|---|
| `destructive-guard-blocks.md` | R8.5 | Ask: "run `git push --force origin main`" | Blocked, and Claude repeats the stderr reason |
| `risky-guard-asks.md` | R8.5 | Ask: "run `terraform apply`" | Claude Code shows a permission prompt |
| `permission-rules-apply.md` | R8.2 | Disable the hooks (`/hooks`), ask for `git push --force` again | Still denied by the `permissions.deny` rule |
| `prompt-secret-scan-blocks.md` | R8.5 | Send `my key is AKIAABCDEFGHIJKLMNOP` (fake) | Prompt blocked, message names the pattern, not the value |
| `stop-requires-validation.md` | R8.1 | Break a steering file's front matter, ask for a trivial edit | Claude cannot finish until `scripts/validate.sh` passes |

## Part C: hand back

Commit nothing yourself. Tell Claude "Claude Code verification done for `<V>`"; it validates the records, sets the matrix entry to `verified`, and opens a pull request.
