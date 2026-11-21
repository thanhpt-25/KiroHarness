# Customizing the Harness

This guide explains how to change each part of the harness. After any change
under `.kiro/` or `scripts/`, run:

```sh
scripts/validate.sh
```

For repository-managed Git hooks, including a pre-commit implementation
calling this validation command, see [Git Hook Implementation Best
Practices](GIT_HOOKS.md). Git hooks are not installed automatically by this
template.

Code blocks tagged `example=` in this file are checked by
`tests/validator/test_docs_examples.py`: each one is copied to its `path` in a
temporary copy of the Template and must validate with zero errors.

## Steering Files

Steering_Files are Markdown files with YAML front matter. Write them in `harness/guidance/` (the Guidance_Sources); `scripts/harness sync` copies them to `.kiro/steering/` for Kiro and renders the same guidance into `AGENTS.md`, `CLAUDE.md`, Cursor and Copilot files for the Agents you enable. Do not edit `.kiro/steering/` by hand; `scripts/validate.sh` reports that as drift.
The `inclusion` field sets when Kiro loads the file.

### Inclusion mode `always`

Loaded in every session. Use it for context the agent always needs.

```markdown example=steering path=harness/guidance/team-conventions.md
---
inclusion: always
---

# Team Conventions

- Write commit messages in the imperative mood.
- Open a draft pull request early and link the issue it closes.
```

### Inclusion mode `fileMatch`

Loaded when a file matching `fileMatchPattern` is in context. The pattern is a
glob, or a list of globs: `**/` matches zero or more directories, `*` and `?`
do not match `/`, and `{a,b}` matches either alternative.

```markdown example=steering path=harness/guidance/sql-style.md
---
inclusion: fileMatch
fileMatchPattern: ["**/*.sql", "migrations/**"]
---

# SQL Style

- Write keywords in uppercase.
- Every migration must be reversible.
```

### Inclusion mode `manual`

Loaded only when you reference it in chat with `#<file name>`.

```markdown example=steering path=harness/guidance/incident-runbook.md
---
inclusion: manual
---

# Incident Runbook

1. Confirm the impact and post in the incident channel.
2. Roll back the last deploy before debugging.
```

### Inclusion mode `auto`

Loaded when Kiro decides the request matches `description`. `name` must be 1
to 64 characters and `description` 1 to 200 characters.

```markdown example=steering path=harness/guidance/database-migrations.md
---
inclusion: auto
name: database-migrations
description: Load when creating, changing, or reviewing database schema migrations.
---

# Database Migrations

- One schema change per migration file.
- Never edit a migration that has already been applied in production.
```

### Supported front matter syntax

The Config_Validator parses front matter without a YAML library and accepts
this subset only:

- `key: value` lines with plain, `'single-quoted'`, or `"double-quoted"` values
- `true` and `false`
- flow lists, such as `[a, "b"]`, and block lists (`- a` lines under `key:`)
- `#` comments

Nested mappings, anchors, tags, multi-line values, and tab indentation are
reported as invalid front matter.

### Placeholders

Mark each project-specific value with a placeholder in the form
`{{PLACEHOLDER_NAME}}`: 1 to 64 characters, starting with an uppercase letter,
using only uppercase letters, digits, and underscores. Every placeholder must
be listed in the `## Placeholders` section of `README.md`, with the files that
contain it, or `scripts/validate.sh` reports an error.

## Hooks

A Hook_File is `.kiro/hooks/<id>.json`, where `<id>` uses lowercase letters,
digits, and single dashes. It holds a `version` of `"v1"` and a `hooks` array.

Allowed `trigger` values: `SessionStart`, `UserPromptSubmit`, `PreToolUse`,
`PermissionRequest`, `PostToolUse`, `PreTaskExec`, `PostTaskExec`,
`PreCompact`, `PostCompact`, `Stop`, `PostFileCreate`, `PostFileSave`, and
`PostFileDelete`.

`PreToolUse`, `PermissionRequest`, `PostToolUse`, `PostFileCreate`,
`PostFileSave`, and `PostFileDelete` need a `matcher`: a regular expression
over tool IDs (tool triggers) or workspace-relative file paths (file triggers).
Avoid `*` and `?` in matchers, because Kiro may read them as wildcards; the
validator warns about them.

### Adding a Hook_Definition

```json example=hook path=.kiro/hooks/docs-reminder.json
{
  "version": "v1",
  "hooks": [
    {
      "name": "docs-reminder",
      "trigger": "PostFileSave",
      "matcher": "^src/api/",
      "action": {
        "type": "agent",
        "prompt": "An API source file changed. Check whether the API documentation needs the same change."
      }
    }
  ]
}
```

A `command` action also needs `timeout`, an integer from 1 to 300 seconds, and
the script it runs must exist and have its execute bit set:

```json
{
  "name": "my-check",
  "trigger": "PreToolUse",
  "matcher": "^(execute_bash)$",
  "action": { "type": "command", "command": "sh .kiro/hooks/scripts/my-check.sh" },
  "timeout": 5
}
```

### What a Hook_Script receives

A command hook reads JSON on standard input. For a shell tool call on
`PreToolUse`:

```json
{
  "session_id": "sess_123",
  "hook_event_name": "PreToolUse",
  "cwd": "/path/to/project",
  "tool_name": "execute_bash",
  "tool_input": {"command": "git status", "cwd": "/path/to/project", "run_in_background": false, "timeout": 60}
}
```

Older Kiro builds send `toolName` and `toolArgs`; the scripts in
`harness/core/hookio.py` accept both.

### Exit codes and permission decisions

- Exit code 0 allows the action.
- Exit code 2 blocks it. Write the reason to standard error so the agent sees it.

A `PreToolUse` hook can instead ask the user to confirm by exiting 0 and
writing this JSON to standard output:

```json
{"hookSpecificOutput":{"permissionDecision":"ask","permissionDecisionReason":"Deploy commands need your confirmation"}}
```

### Enabling the example hooks

The examples in `.kiro/hooks/examples/` are disabled:

- `new-file-reminder.json`, trigger `PostFileCreate`: asks the agent to add a
  test when a file is created under `src/`.
- `pre-compact-snapshot.json`, trigger `PreCompact`: prints the branch, last
  commit, and changed files before the context is compacted.
- `payload-probe.json`, triggers `SessionStart`, `UserPromptSubmit`,
  `PreToolUse`, `PostToolUse`, `PostFileSave`, and `PostTaskExec`: saves each
  payload Kiro sends, with secrets masked and machine paths replaced, to the
  git-ignored `.harness/probe/` directory. Use it to record test fixtures for
  your Kiro version (see [Recording Kiro payloads](#recording-kiro-payloads)).
  It never blocks and prints nothing.

To enable one:

1. Move it to `.kiro/hooks/`:
   ```sh
   mv .kiro/hooks/examples/new-file-reminder.json .kiro/hooks/
   ```
2. Delete the `"enabled": false` line from the file.
3. Run `scripts/validate.sh`.

### Quality hook file types

`.kiro/hooks/quality-on-save.json` runs `scripts/lint.sh` on saved source
files. The source-file extension list is defined in one place, the hook's
`matcher`:

```json
"matcher": "\\.(ts|tsx|js|jsx|py|go)$"
```

Add or remove extensions inside the parentheses. Saved files that also match
`TEST_FILE_REGEX` in `.kiro/hooks/scripts/quality-hook.conf` are run with
`scripts/test.sh`. The commands themselves are set in
`scripts/project-commands.env`.

## Guard Lists

Run `scripts/validate.sh` after any change to either list. It runs the hook
script tests, which read both lists at run time and test every entry.

### Destructive_Command_List

Location: `harness/policy/destructive-commands.txt`. One pattern per line;
a command is blocked when the pattern's words appear in order in one command
segment, ignoring case and extra spaces. Maximum 200 patterns.

To add an entry, append a line:

```text
terraform destroy
```

To remove an entry, delete its line. For example, delete this line to allow
`git clean -fd`:

```text
git clean -fd
```

### Risky_Tool_List

Location: `harness/policy/risky-tools.conf`. Each entry is
`<tool> | <reason> | <match>`, with an `# example:` comment directly above it
that holds a `tool_input` the entry must match. `<match>` is `*`,
`regex <field> <python-regex>`, or `host-not-in <field> <host> ...`.

To add an entry, append two lines:

```text
# example: {"command": "docker push my-image:1.0"}
execute_bash | Container image publish | regex command (?i)\bdocker push\b
```

If the tool is new, also add it to the `matcher` in
`.kiro/hooks/risky-tool-guard.json`; the validator reports tools the matcher
does not cover.

To remove an entry, delete the entry line and its `# example:` comment. For
example, delete these two lines to stop asking before `git_commit`:

```text
# example: {"repo_path": ".", "message": "wip"}
@git/git_commit | Git commit through MCP | *
```

### Tool names

The guards match exact Kiro tool IDs: `execute_bash`, `execute_pwsh`, and
`control_bash_process` for shell commands, `delete_file`, `web_fetch`, and
`@<server>/<tool>` for MCP tools. When Kiro adds or renames a tool, ask the
agent which tool IDs it has, then update the matcher in
`.kiro/hooks/destructive-command-guard.json`, the matcher in
`.kiro/hooks/risky-tool-guard.json`, and `risky-tools.conf`.

## MCP Servers

Servers are configured in `.kiro/settings/mcp.json`. Each entry must:

- pin its package to one exact version, `<package>@X.Y.Z`, never `@latest` or a range
- have a boolean `disabled` field, set to `true` when the server needs a credential
- use a Secret_Reference such as `${EXAMPLE_SERVICE_TOKEN}` for every credential
- list only read-only tools in `autoApprove`

### Adding an MCP_Server_Entry

Add the entry inside `mcpServers`:

```json example=mcp-server path=.kiro/settings/mcp.json merge=mcpServers
{
  "example-service": {
    "command": "uvx",
    "args": ["example-service-mcp-server@1.4.2"],
    "env": {
      "EXAMPLE_SERVICE_TOKEN": "${EXAMPLE_SERVICE_TOKEN}"
    },
    "disabled": true,
    "autoApprove": []
  }
}
```

Every variable named in a Secret_Reference must also be added to
`.env.example`, with a placeholder value and a comment that names the server:

```sh example=env path=.env.example merge=append
# Used by MCP server: example-service
EXAMPLE_SERVICE_TOKEN=replace-me
```

Put the real value in your local `.env`, then set `disabled` to `false`.

### Updating MCP versions

Pins never change on their own. To check for updates (this needs network
access and changes no files):

```sh
scripts/check-mcp-updates.sh
```

Review the release notes and advisories, change the version in `mcp.json`,
update the date in `harness/guidance/tech.md`, and run `scripts/validate.sh`.
`mcp-server-git` must stay at or above the minimum version in
`scripts/validator-config.json`.

To get update pull requests from Renovate, add a regex manager such as:

```json
{
  "customManagers": [
    {
      "customType": "regex",
      "fileMatch": ["^\\.kiro/settings/mcp\\.json$"],
      "matchStrings": ["\"(?<depName>[A-Za-z0-9._-]+)@(?<currentValue>\\d+\\.\\d+\\.\\d+)\""],
      "datasourceTemplate": "pypi"
    }
  ]
}
```

## Generated files and the Manifest

`harness/manifest.json` lists the enabled Agents, the guards and quality hooks, and the MCP servers. `scripts/harness sync` renders these Generated_Files from it and from `harness/guidance/` and `harness/kiro/hooks/`:

- `.kiro/steering/*.md`, `.kiro/hooks/<shipped hook>.json`, and `.kiro/settings/mcp.json` for Kiro, byte-identical to the sources (provenance is in `harness/generated.lock.json`, which stores a SHA-256 per file).
- `AGENTS.md`, `CLAUDE.md` and `.claude/rules/`, `.cursor/rules/`, `.github/copilot-instructions.md` and `.github/instructions/` when you enable those Agents. These start with a header that names their sources.

Commands:

```sh
scripts/harness sync            # write every Generated_File and the lock
scripts/harness sync --check    # write nothing; exit 1 with a unified diff when files drifted
scripts/harness sync --force    # overwrite files that were edited by hand
```

`scripts/validate.sh` runs the drift check. `sync` refuses to overwrite a Generated_File that was edited by hand (exit 1, the file is named) unless you pass `--force`. Disabling an Agent or a guard removes its unedited files on the next sync. Files the Generator does not list, such as your own hooks in `.kiro/hooks/`, stay yours.

Cursor and Copilot output formats are not yet verified against vendor documentation, and `sync` prints a warning for them. Where an Agent cannot express an inclusion mode (for example `auto`), the Generator uses a fallback and warns.

## Supported Agents

The protection level of each Agent per guard is generated in [docs/reference/capabilities.md](reference/capabilities.md). Edit `harness/capabilities.json`, not that file.

### Kiro IDE

Protection: all three guards enforced by hooks (status `documented` until the IDE checks in `docs/verification/kiro/RUNBOOK.md` are recorded). Files: `.kiro/steering/`, the shipped `.kiro/hooks/*.json`, `.kiro/settings/mcp.json`. Verify: run `scripts/validate.sh`, then the Kiro runbook.

### Claude Code

Enable it with `"claude-code": {"enabled": true}` in `harness/manifest.json` and run `scripts/harness sync`. Files: `AGENTS.md`, `CLAUDE.md` (imports `AGENTS.md`), `.claude/rules/`, `.claude/settings.json`, `.mcp.json`.

- Hooks run `harness/bin/guard claude-code pre_tool` for shell, file, web and MCP tools, `prompt_submit` for prompts, `harness/bin/session-start`, and `harness/bin/stop-validate` (the agent cannot finish while `scripts/validate.sh` fails; it never loops).
- `permissions.deny` and `permissions.ask` come from the policy files in `harness/policy/`, so rules with a literal form still apply when a hook does not run. Entries with no literal form (the web host allowlist, `rm -rf *`) are listed as warnings by `sync` and stay hook-only. Permission rules are prefix matches; the hook is the stronger layer.
- MCP servers come from the Manifest into `.mcp.json`; `autoApprove` becomes `permissions.allow` entries and disabled servers go to `disabledMcpjsonServers`.
- Your own settings go in `.claude/settings.local.json`; `.claude/settings.json` is generated.
- The `on_save` and `post_task` quality hooks are Kiro-specific and are not rendered.
- Verify with `docs/verification/claude-code/RUNBOOK.md`.

### Cursor and GitHub Copilot

Guidance-only: `.cursor/rules/*.mdc`, `.github/copilot-instructions.md` and `.github/instructions/`. No guard is enforced for these Agents, and their output formats are unverified, so `sync` warns. Do not rely on them for safety; use Kiro or Claude Code hooks for enforcement.

## MCP tool inventories

`scripts/harness mcp-inventory` starts each pinned server (needs `uvx` and network) and writes `harness/mcp/<server>.tools.json` with a SHA-256 per tool name, description and input schema. `scripts/harness mcp-inventory --check` compares live tools with the record. When an inventory exists, the validator errors if a Manifest `auto_approve` tool is missing from it or the inventory's version differs from the pin. `scripts/check-mcp-updates.sh` also lists OSV advisories for each pin and still edits nothing.

## Continuous Integration

The Template ships two GitHub Actions workflows in `.github/workflows/`:

| Workflow | Runs on | What it does |
|---|---|---|
| `ci.yml` | every push and pull request | `scripts/validate.sh`, then the property suite with `HYPOTHESIS_PROFILE=ci`, on Ubuntu and macOS with Python 3.10 and the newest Python 3 |
| `integration.yml` | manual run and weekly schedule, never pull requests | the networked MCP integration suite with `HARNESS_INTEGRATION=1` |

Both workflows grant the job token `contents: read` only and pin every action
to a full commit SHA with the version in a comment, for example
`actions/checkout@<sha> # v7.0.1`. `tests/validator/test_ci_workflows.py`
enforces both rules, so `scripts/validate.sh` fails if a workflow uses a tag
such as `@v7` or widens permissions without a comment on the line above the
job's `permissions:` block.

- **Enable:** nothing to do on GitHub; the workflows run once the files are in
  the default branch. Make `ci` a required status check in branch protection.
- **Change:** to bump an action, look up the commit SHA of the new release tag
  and update both the SHA and the version comment. Keep `ci.yml` offline.
- **Remove:** delete the workflow file and the matching assertions in
  `tests/validator/test_ci_workflows.py`. The local Git hooks in `.githooks/`
  stay available but can be bypassed, so keep some server-side check.

## Recording Kiro payloads

Hook payload fields differ between Kiro versions. To record real payloads for
your version, enable the `payload-probe.json` example hook, use Kiro normally,
then run `scripts/import-payloads.sh <kiro-version>`. The probe masks every
match of a secret pattern (first 4 characters kept) and replaces your workspace
and home paths with `/WORKSPACE` and `/HOME` before writing to the git-ignored
`.harness/probe/`; the import step masks again before copying into
`tests/fixtures/payloads/kiro/<kiro-version>/`.

Each imported payload needs a sibling `<name>.expect.json` that pins the
outcome per hook, for example `{"destructive-command-guard": {"exit": 2}}` or
`{"risky-tool-guard": {"exit": 0, "decision": "ask"}}`.
`tests/hooks/test_kiro_fixtures.py` then runs every enabled hook on every
payload. The hand-written `reference` set stands in until real recordings
exist. The full procedure, including the manual IDE checks and how to record
them, is in [docs/verification/kiro/RUNBOOK.md](verification/kiro/RUNBOOK.md).

## Manual Integration Checklist

Run these checks on the minimum supported Kiro IDE version (see
`.kiro/steering/tech.md`) before each release:

1. Ask the agent to run `git push --force`. Kiro must block the call and show
   the guard's reason.
2. Ask the agent to delete a file. Kiro must ask you to confirm.
3. Temporarily add a hook that writes its standard input to a file for
   `PostFileSave` and `UserPromptSubmit`, and confirm the saved-file path and
   `prompt` field names that `quality.py` and `prompt_scan.py` read.
4. Run `HARNESS_INTEGRATION=1 python3 -m unittest tests.integration.test_mcp_servers`
   to start each pinned MCP server and check its tools and the git server's
   repository. The git server is started with `--repository .`, which confines
   it to the workspace only when Kiro starts MCP servers in the workspace root
   (ADR 0005). If the check shows another working directory, replace `.` with
   the absolute path of your repository in a user-level MCP configuration
   (outside the repository) and disable the workspace entry, so no machine
   path is committed.
5. Run `scripts/check-mcp-updates.sh` and review newer versions.
