# Policy_File formats

Policy files live in `harness/policy/` and are read at run time by every guard, so a change needs no code edit. Run `scripts/validate.sh` after changing one. Blank lines and lines starting with `#` are ignored.

## destructive-commands.txt
One pattern per line, at most 200. A pattern is a list of literal words; a command matches when the words appear in order within one command segment (segments split on `&&`, `||`, `;`, `|` and newlines). Matching ignores case and whitespace runs. A match, an unreadable file or malformed input blocks the call (fail closed).

```text example=destructive-entry path=harness/policy/destructive-commands.txt merge=append
docker system prune
```

## risky-tools.conf
One entry per line: `tool | reason | predicate`. The tool column is `category:<name>` (`shell`, `read`, `write`, `delete`, `web`), `<agent>:<tool-id>` for one Agent, or a bare Kiro tool ID. The predicate is `*` (always ask), `regex <field> <pattern>`, or `host-not-in <field> @<file>` (hosts read from a file in the same folder). An entry may be preceded by `# example: <json>` giving a call that must ask; tests run every example. Unusable input or policy asks instead of allowing (fail to ask).

## protected-paths.txt
Glob patterns for files agents must not read, write or delete, plus shell commands that read them. A line starting with `!` re-includes paths an earlier pattern excluded. A missing or unreadable file blocks the call (fail closed).

## egress-allowlist.txt
One host per line. A `web` call to a host that is not listed asks for approval (through the `host-not-in` predicate in `risky-tools.conf`).

## Related
- [Command reference](cli.md), [Capability matrix](capabilities.md)
- Known gaps of the pattern-based guards: [Customization Guide](../CUSTOMIZING.md#known-gaps-and-limits)
