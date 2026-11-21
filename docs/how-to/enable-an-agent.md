# How to enable another Agent

Edit `harness/manifest.json` (never the generated files) and run `scripts/harness sync`. For Claude Code, add the Agent to the `agents` object:

```json example=manifest-agents
{"claude-code": {"enabled": true}}
```

If the project already has a hand-written `CLAUDE.md` (or another file the Generator would write), `sync` refuses to overwrite it. Move its content into a file in `harness/guidance/`, then run `scripts/harness sync --force` once.

Then run `scripts/harness sync --check` (no output means no drift) and `scripts/validate.sh`. `sync` prints a warning for every rule it could not express natively for that Agent. Read [Capability matrix](../reference/capabilities.md) to see which layers (hook, permission rule, guidance) each Agent has; Cursor and Copilot get guidance only.

Claude Code and the other Agents' output formats are documented but not yet verified against a real installation; the checks to run are in `docs/verification/claude-code/RUNBOOK.md`.
