# Manual verification records

Some behavior cannot be tested offline, for example whether Kiro IDE blocks a
tool call when a hook exits 2. Each such check is recorded here as a
Manual_Check_Record, so a claim like "the guard works in Kiro 1.x" has a date,
a version, and a result behind it.

## Layout

```text
docs/verification/<agent>/<agent-version>/<check>.md
```

Files directly in this directory (this README and `TEMPLATE.md`) are not
records. `scripts/validate.sh` checks every record's front matter.

## Front matter

| Field | Meaning |
|---|---|
| `criteria` | List of `<spec>/R<n>.<m>` the check validates |
| `agent` | Agent key; must equal the `<agent>` directory |
| `agent_version` | Exact version tested; must equal the `<agent-version>` directory |
| `os` | Operating system and version |
| `date` | `YYYY-MM-DD` the check was run |
| `verdict` | `pass`, `fail`, or `partial` |

Body sections: `## Steps`, `## Observed`, `## Notes`.

A `fail` or `partial` verdict is a valid, useful record: it documents a gap and
drives the fallback described in `docs/CUSTOMIZING.md`.

## Records are never edited to change a verdict

Re-run the check on the new version and add a new record in that version's
directory. Keep old records; they show when behavior changed.

See [kiro/RUNBOOK.md](kiro/RUNBOOK.md) for the Kiro checks.
