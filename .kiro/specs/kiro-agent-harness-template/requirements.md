# Requirements Document

## Introduction

The Kiro Agent Harness Template is a reusable starter project for Kiro IDE. A developer copies the Template into a new or existing repository to get a working agent harness: steering files that give the agent project context, agent hooks that enforce safety and quality checks, a workspace-level MCP server configuration, an example spec, and documentation that explains how to customize each part.

The Template follows these practices: least privilege for tools and MCP servers, secrets kept out of the repository, hooks that block destructive commands and ask before risky tool use, lint and test checks on file save, and validation scripts that check the Template's own configuration files.

## Glossary

- **Template**: The complete set of files in this repository that a developer copies to start a Kiro-enabled project.
- **Steering_File**: A Markdown file in `.kiro/steering/` that gives the agent project context. Each Steering_File has YAML front matter that declares an inclusion mode.
- **Inclusion_Mode**: The front-matter value that controls when Kiro loads a Steering_File. Allowed values are `always`, `fileMatch`, `manual`, and `auto`.
- **File_Match_Pattern**: The glob pattern in a Steering_File's front matter that selects the files for which a `fileMatch` Steering_File is loaded.
- **Hook_File**: A JSON file at `.kiro/hooks/<id>.json` that follows the schema `{"version":"v1","hooks":[{"name","trigger","matcher","action"}]}`. The `matcher` field is optional, except where Requirement 3 criteria 6 and 7 require it.
- **Hook_Definition**: One entry in the `hooks` array of a Hook_File.
- **Hook_Trigger**: The event that fires a Hook_Definition. Allowed values are `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreTaskExec`, `PostTaskExec`, `PreCompact`, `PostCompact`, `Stop`, `PostFileCreate`, `PostFileSave`, and `PostFileDelete`.
- **Matcher_Required_Trigger**: A Hook_Trigger for which a Hook_Definition must specify a `matcher`: `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PostFileCreate`, `PostFileSave`, and `PostFileDelete`.
- **Hook_Action**: The `action` object of a Hook_Definition. A Hook_Action has type `command` (runs a shell command) or type `agent` (appends a prompt to the agent context).
- **Hook_Script**: A shell script in `.kiro/hooks/scripts/` that a `command` Hook_Action runs. A Hook_Script reads hook context as JSON on standard input.
- **Destructive_Command_Guard**: The Hook_Script, fired on `PreToolUse`, that inspects shell commands the agent is about to run and blocks commands on the Destructive_Command_List.
- **Destructive_Command_List**: A configurable list of command patterns treated as destructive, for example `rm -rf /`, `git push --force`, `git reset --hard`, `git clean -fd`, `DROP TABLE`, and `mkfs`.
- **Risky_Tool_Guard**: The Hook_Script, fired on `PreToolUse`, that returns `permissionDecision` `"ask"` for tool calls on the Risky_Tool_List.
- **Risky_Tool_List**: A configurable list of tool names and argument patterns that require user confirmation, for example file deletion, network fetches to unlisted hosts, and deploy commands.
- **Quality_Hook**: A Hook_Definition, fired on `PostFileSave`, that runs the project's lint and test commands for the saved file.
- **Lint_Command**: The project lint command defined in `scripts/`, which the Quality_Hook runs against a single file path.
- **Test_Command**: The project test command defined in `scripts/`, which the Quality_Hook and the `PostTaskExec` Hook_Definition run in single-run mode.
- **Validation_Command**: The single command in `scripts/` that runs the Config_Validator and all hook script tests in one invocation (Requirement 11 criterion 5).
- **MCP_Config**: The workspace-level MCP server configuration file at `.kiro/settings/mcp.json`.
- **MCP_Server_Entry**: One server entry in the `mcpServers` object of the MCP_Config, containing `command`, `args`, optional `env`, `disabled`, and optional `autoApprove` fields.
- **Secret_Reference**: An environment variable placeholder in the form `${VAR_NAME}` used in place of a literal secret value.
- **Secret_Pattern_List**: The list of regular expressions, kept in the Config_Validator's configuration, that identify literal secret values (for example API keys, access tokens, and private keys). Also referred to as the Config_Validator secret pattern list.
- **Read_Only_Allowlist**: The list of MCP tool names, kept in the Config_Validator's configuration, that are known to be read-only and may appear in an `autoApprove` list.
- **Placeholder**: A token in the form `{{PLACEHOLDER_NAME}}` that marks a project-specific value the developer must replace.
- **Env_Example_File**: The file `.env.example` that lists every environment variable the Template uses, with placeholder values only.
- **Example_Spec**: A sample spec in `.kiro/specs/example-feature/` containing `requirements.md`, `design.md`, and `tasks.md`.
- **Config_Validator**: The validation script in `scripts/` that checks Steering_Files, Hook_Files, and the MCP_Config for structural and safety errors.
- **Hook_Config_Parser**: The component of the Config_Validator that reads a Hook_File into an in-memory Hook configuration object.
- **Hook_Config_Printer**: The component of the Config_Validator that writes an in-memory Hook configuration object back to Hook_File JSON.
- **Validation_Report**: The output of the Config_Validator, listing each error and warning with file path, field path, and message.
- **Template_README**: The `README.md` file at the root of the Template.
- **Customization_Guide**: The document at `docs/CUSTOMIZING.md` that explains how to adapt each part of the Template.

## Requirements

### Requirement 1: Template Directory Structure

**User Story:** As a developer, I want a predictable directory layout, so that I can find and change each part of the harness without searching.

#### Acceptance Criteria

1. THE Template SHALL contain the directories `.kiro/steering/`, `.kiro/hooks/`, `.kiro/hooks/scripts/`, `.kiro/settings/`, `.kiro/specs/`, `.kiro/specs/example-feature/`, `scripts/`, and `docs/`, each relative to the Template root and each containing at least one file tracked in version control.
2. THE Template SHALL contain the files `README.md`, `docs/CUSTOMIZING.md`, `.env.example`, `.gitignore`, `.kiro/settings/mcp.json`, `.kiro/specs/example-feature/requirements.md`, `.kiro/specs/example-feature/design.md`, and `.kiro/specs/example-feature/tasks.md`, each relative to the Template root and each with a size greater than 0 bytes.
3. THE Template SHALL list ignore patterns in the `.gitignore` file such that `git check-ignore` reports `.env`, `.env.local`, `.env.production`, and `.kiro/settings/mcp.local.json` as ignored and reports `.env.example` and `.kiro/settings/mcp.json` as not ignored.
4. THE Template SHALL set the owner execute permission bit on every Hook_Script and every shell script in `scripts/`, and the version-control file mode of each of these scripts SHALL be recorded as executable.
5. THE Template SHALL begin every Hook_Script and every shell script in `scripts/` with an interpreter line (`#!`) on line 1.

### Requirement 2: Steering Files

**User Story:** As a developer, I want steering files covering product, technology, structure, coding standards, security, and testing, so that the agent works with accurate project context from the first session.

#### Acceptance Criteria

1. THE Template SHALL provide Steering_Files named `product.md`, `tech.md`, `structure.md`, `coding-standards.md`, `security.md`, and `testing.md` in `.kiro/steering/`, each starting with a YAML front matter block delimited by `---` lines that declares exactly one Inclusion_Mode from the allowed values `always`, `fileMatch`, `manual`, and `auto`.
2. THE Template SHALL set the Inclusion_Mode of `product.md`, `tech.md`, `structure.md`, and `security.md` to `always`.
3. THE Template SHALL set the Inclusion_Mode of `testing.md` to `fileMatch` with a File_Match_Pattern that matches the example paths `src/app.test.ts`, `src/app.spec.js`, `tests/test_app.py`, and `test/app_test.go`, and does not match the example paths `src/app.ts` and `README.md`.
4. THE Template SHALL set the Inclusion_Mode of `coding-standards.md` to `fileMatch` with a File_Match_Pattern that matches the example paths `src/app.ts`, `src/app.tsx`, `src/app.js`, `src/app.py`, and `src/app.go`, and does not match the example paths `README.md`, `.env.example`, and `.kiro/settings/mcp.json`.
5. THE Template SHALL provide, in addition to the six Steering_Files named in criterion 1, at least one Steering_File in `.kiro/steering/` with Inclusion_Mode `manual` and at least one Steering_File in `.kiro/steering/` with Inclusion_Mode `auto`.
6. WHERE a Steering_File has Inclusion_Mode `auto`, THE Steering_File SHALL include in the front matter a non-empty `name` field of 1 to 64 characters and a non-empty `description` field of 1 to 200 characters that states when the agent should load the Steering_File.
7. THE Template SHALL mark each project-specific value in a Steering_File with a placeholder in the form `{{PLACEHOLDER_NAME}}`, where `PLACEHOLDER_NAME` is 1 to 64 characters, starts with an uppercase letter, and contains only uppercase letters, digits, and underscores.
8. THE `security.md` Steering_File SHALL state the rules for least privilege, secrets handling through environment variables, input validation at trust boundaries, and confirmation before destructive actions, with each of these four rules under its own Markdown heading.
9. IF a Steering_File in `.kiro/steering/` has no front matter block, has no Inclusion_Mode, or has an Inclusion_Mode outside the allowed values, THEN THE Config_Validator SHALL add an error to the Validation_Report that gives the Steering_File path and the invalid or missing field.
10. IF a Steering_File has Inclusion_Mode `fileMatch` and has no File_Match_Pattern or an empty one, THEN THE Config_Validator SHALL add an error to the Validation_Report that gives the Steering_File path and names the missing File_Match_Pattern.
11. IF a Steering_File has Inclusion_Mode `auto` and its `name` or `description` field is missing, empty, or longer than the limit in criterion 6, THEN THE Config_Validator SHALL add an error to the Validation_Report that gives the Steering_File path and the field that failed.

### Requirement 3: Hook File Format

**User Story:** As a developer, I want every hook to use the documented v1 hook schema, so that Kiro loads the hooks without errors.

#### Acceptance Criteria

1. THE Template SHALL store each hook group in a separate Hook_File at `.kiro/hooks/<id>.json`, where `<id>` is 1 to 64 characters long, contains only lowercase letters `a`–`z`, digits `0`–`9`, and single dashes between those characters, and does not start or end with a dash.
2. THE Template SHALL set the `version` field of every Hook_File to the exact string `"v1"` and SHALL include a `hooks` array that contains at least 1 Hook_Definition.
3. THE Template SHALL give every Hook_Definition a `name` that is a non-empty string of at most 64 characters and unique within its Hook_File, a `trigger` that exactly matches one of the allowed Hook_Trigger values (case-sensitive), and an `action` whose `type` is either `command` or `agent`.
4. WHERE a Hook_Action has type `command`, THE Hook_Definition SHALL specify a non-empty `command` string and a `timeout` value that is an integer from 1 to 300 seconds inclusive.
5. WHERE a Hook_Action has type `agent`, THE Hook_Definition SHALL specify a `prompt` field that is a non-empty string.
6. WHERE a Hook_Definition uses a `PreToolUse`, `PermissionRequest`, or `PostToolUse` trigger, THE Hook_Definition SHALL specify a non-empty `matcher` that compiles as a valid regular expression and selects the targeted tool names.
7. WHERE a Hook_Definition uses a `PostFileCreate`, `PostFileSave`, or `PostFileDelete` trigger, THE Hook_Definition SHALL specify a non-empty `matcher` that compiles as a valid regular expression and selects the targeted file paths.
8. IF a Hook_File violates any rule in criteria 1 through 7, THEN THE Config_Validator SHALL add one error to the Validation_Report for each violation, listing the Hook_File path, the field path of the offending field, and a message naming the broken rule, and SHALL exit with a non-zero status.
9. IF a Hook_File is not parseable JSON, THEN THE Config_Validator SHALL add an error to the Validation_Report that lists the Hook_File path and a message indicating the parse failure, and SHALL continue validating the remaining Hook_Files.

### Requirement 4: Destructive Command Guard

**User Story:** As a developer, I want the agent blocked from running destructive shell commands, so that an agent mistake cannot delete data or rewrite shared history.

#### Acceptance Criteria

1. THE Template SHALL provide a Hook_File containing a Hook_Definition with Hook_Trigger `PreToolUse`, a `matcher` that selects only shell execution tools, and a `command` Hook_Action that runs the Destructive_Command_Guard, so that the Destructive_Command_Guard does not run for tool calls of non-shell tools.
2. WHEN the Destructive_Command_Guard receives a command that matches an entry in the Destructive_Command_List, THE Destructive_Command_Guard SHALL exit with code 2 and write to standard error the matched pattern and a reason stating that the command is on the Destructive_Command_List, where a match is evaluated ignoring letter case and treating any run of one or more whitespace characters as a single space.
3. WHEN the Destructive_Command_Guard receives a command that matches no entry in the Destructive_Command_List, THE Destructive_Command_Guard SHALL exit with code 0 and write nothing to standard error.
4. IF the Destructive_Command_Guard receives standard input that is not valid JSON, or that is valid JSON but lacks a non-empty string value for the shell command, THEN THE Destructive_Command_Guard SHALL exit with code 2 and write to standard error a message indicating that the hook input could not be parsed or that the command field is missing.
5. THE Destructive_Command_Guard SHALL read the Destructive_Command_List from a separate configuration file in `.kiro/hooks/scripts/` that holds one pattern per line, ignores blank lines and lines starting with `#`, and supports up to 200 patterns.
6. WHEN the Destructive_Command_Guard receives a chained command, meaning segments joined by `&&`, `||`, `;`, `|`, or a newline, and any one segment matches an entry in the Destructive_Command_List, THE Destructive_Command_Guard SHALL exit with code 2 and write the matched pattern and reason to standard error, as in criterion 2.
7. THE Destructive_Command_Guard SHALL complete each check and exit within 2 seconds for a command of up to 10,000 characters checked against a Destructive_Command_List of up to 200 patterns.
8. IF the Destructive_Command_List configuration file is missing, unreadable, or contains zero patterns, THEN THE Destructive_Command_Guard SHALL exit with code 2 and write to standard error a message that names the configuration file path and says the list could not be loaded, so that commands are blocked rather than allowed when the list is unavailable.

### Requirement 5: Risky Tool Guard

**User Story:** As a developer, I want the agent to ask me before risky tool calls, so that I keep control of actions with side effects outside the workspace.

#### Acceptance Criteria

1. THE Template SHALL provide a Hook_File that runs the Risky_Tool_Guard on the `PreToolUse` trigger, with a Hook_Definition `matcher` that covers every tool name in the Risky_Tool_List.
2. WHEN the Risky_Tool_Guard receives a tool call whose tool name equals the tool name of a Risky_Tool_List entry and whose arguments match that entry's argument pattern (or the entry has no argument pattern), THE Risky_Tool_Guard SHALL exit with code 0 and write `{"hookSpecificOutput":{"permissionDecision":"ask","permissionDecisionReason":"<reason>"}}` as the only content on standard output.
3. WHEN the Risky_Tool_Guard receives a tool call that matches no entry in the Risky_Tool_List, THE Risky_Tool_Guard SHALL exit with code 0 and write nothing to standard output.
4. THE Risky_Tool_Guard SHALL read the Risky_Tool_List from a separate configuration file in `.kiro/hooks/scripts/`, and the Template's default Risky_Tool_List SHALL contain at least one entry each for file deletion, network fetches to hosts not on an allowlist, and deploy commands.
5. WHEN the Risky_Tool_Guard returns a permission decision of `"ask"`, THE Risky_Tool_Guard SHALL include the matched tool name and the matched Risky_Tool_List entry in the `permissionDecisionReason` value.
6. IF the Risky_Tool_Guard receives standard input that is not valid JSON or that has no tool name field, THEN THE Risky_Tool_Guard SHALL exit with code 0, write a permission decision of `"ask"` to standard output with a `permissionDecisionReason` stating that the hook input could not be parsed, and write a parse error message to standard error.
7. IF the Risky_Tool_List configuration file is missing, unreadable, or not in the expected format, THEN THE Risky_Tool_Guard SHALL exit with code 0, write a permission decision of `"ask"` to standard output with a `permissionDecisionReason` that names the configuration file problem, and write an error message naming the configuration file path to standard error.
8. THE Risky_Tool_Guard SHALL complete each check within 2 seconds.

### Requirement 6: Quality Hooks on File Save

**User Story:** As a developer, I want lint and tests to run when files are saved, so that the agent and I see failures right after a change.

#### Acceptance Criteria

1. THE Template SHALL provide a Quality_Hook on the `PostFileSave` trigger whose `matcher` selects only files with an extension on a source-file extension list, where the list is defined in one place in the Quality_Hook configuration and documented in the Customization_Guide.
2. WHEN a file matching the Quality_Hook matcher is saved, THE Quality_Hook SHALL run the lint command defined in `scripts/` with the saved file's path as its only target, so that no other files are linted.
3. WHEN a saved file matches the Quality_Hook matcher and also matches the test-file name pattern defined in the Quality_Hook configuration, THE Quality_Hook SHALL run the test command defined in `scripts/` for that test file only, in single-run mode, where single-run mode means the test process exits after one pass and does not watch for further changes.
4. IF the lint command or the test command is not configured, meaning its definition in `scripts/` is empty or absent, THEN THE Quality_Hook SHALL skip that command, exit with code 0, and write a message naming the missing command to standard output.
5. THE Quality_Hook SHALL set a `timeout` of 120 seconds or less.
6. IF the lint command or the test command exits with a non-zero code, THEN THE Quality_Hook SHALL exit with a non-zero code and write a message to its output, visible to the agent, that names the failing command and the saved file path and includes the failing command's output, truncated to its last 200 lines.
7. IF the lint command or the test command is still running when the Quality_Hook `timeout` expires, THEN THE Quality_Hook SHALL stop that command, exit with a non-zero code, and write a message stating that the named command timed out for the saved file path.
8. WHEN every configured command run for a saved file exits with code 0, THE Quality_Hook SHALL exit with code 0 and write a message naming each command that passed for the saved file path.

### Requirement 7: Session and Workflow Hooks

**User Story:** As a developer, I want hooks for session start, prompt submission, task execution, and agent stop, so that the template shows how each lifecycle trigger is used.

#### Acceptance Criteria

1. WHEN a Kiro session starts, THE `SessionStart` Hook_Definition provided by the Template SHALL write the current git branch name and the count of uncommitted files (staged, modified, and untracked) to standard output, exit with code 0, and use a `timeout` of 10 seconds or less.
2. WHEN the developer submits a prompt that contains a value matching any pattern from the Config_Validator secret pattern list, THE `UserPromptSubmit` Hook_Definition provided by the Template SHALL exit with code 2 and write to standard error a message naming the matched pattern, without including the matched value, using a `timeout` of 5 seconds or less.
3. WHEN a spec task finishes executing, THE `PostTaskExec` Hook_Definition provided by the Template SHALL run the test command defined in `scripts/` in single-run mode, exit with code 0 if all tests pass and code 2 if any test fails, and use a `timeout` of 300 seconds or less.
4. WHEN the agent stops, THE `Stop` Hook_Definition provided by the Template SHALL use an `agent` Hook_Action whose `prompt` names the validation command defined in `scripts/` and instructs the agent to confirm that the command exited with code 0 before finishing.
5. WHERE a Hook_Definition is an example and not enabled by default, THE Template SHALL store its Hook_File in `.kiro/hooks/examples/`, and THE Customization_Guide SHALL name the Hook_File, state its trigger, and give the steps to enable it.
6. IF the workspace is not a git repository or the `git` command is not available, THEN THE `SessionStart` Hook_Definition SHALL write a message to standard output indicating that git information is unavailable and exit with code 0.
7. IF a submitted prompt contains no value matching any pattern from the Config_Validator secret pattern list, THEN THE `UserPromptSubmit` Hook_Definition SHALL exit with code 0 and write nothing to standard error.
8. IF the test command is not configured in `scripts/`, THEN THE `PostTaskExec` Hook_Definition SHALL exit with code 0 and write a message naming the missing test command to standard output.

### Requirement 8: MCP Server Configuration

**User Story:** As a developer, I want a workspace-level MCP configuration with common servers, so that the agent has documentation, fetch, and git tools without manual setup.

#### Acceptance Criteria

1. THE MCP_Config SHALL be a valid JSON file that defines exactly one MCP_Server_Entry each for an AWS documentation server, a fetch server, and a git server, and SHALL set the `command` field of each of these three MCP_Server_Entries to `uvx`.
2. THE MCP_Config SHALL include a `disabled` field with a JSON boolean value (`true` or `false`, not a string) in every MCP_Server_Entry, and SHALL set `disabled` to `false` in every MCP_Server_Entry that requires no credential.
3. THE MCP_Config SHALL use a Secret_Reference in the form `${VAR_NAME}`, where VAR_NAME is 1 to 64 characters of uppercase letters, digits, and underscores and starts with a letter, for every credential, token, password, or key value in an MCP_Server_Entry `env` object, and SHALL contain no literal credential, token, password, or key value anywhere in the file.
4. THE MCP_Config SHALL pin each `uvx` package in the MCP_Server_Entry `args` to one exact version in `major.minor.patch` form, with no version ranges, wildcards, `latest` tag, or unversioned package names.
5. WHERE an MCP_Server_Entry includes an `autoApprove` list, THE MCP_Config SHALL limit that `autoApprove` list to read-only tool names, where a read-only tool is one that does not create, modify, or delete files, does not change git repository state (for example commit, add, reset, checkout, or branch creation), and does not execute shell commands.
6. THE Env_Example_File SHALL list every environment variable referenced by a Secret_Reference in the MCP_Config, once per variable, with a placeholder value that is not a real credential and a comment that names the MCP_Server_Entry that uses the variable.
7. WHERE an MCP_Server_Entry requires a credential, THE MCP_Config SHALL set the `disabled` field of that MCP_Server_Entry to `true`, so that the server does not start until the developer supplies the credential and enables the entry.
8. THE MCP_Config SHALL restrict the git server MCP_Server_Entry `args` to the workspace repository root, so that the git server cannot operate on repositories outside the workspace.
9. IF the MCP_Config contains a literal credential value instead of a Secret_Reference, an unpinned `uvx` package, an `autoApprove` entry that names a tool that is not read-only, or an MCP_Server_Entry without a boolean `disabled` field, THEN THE Config_Validator SHALL record one error per violation in the Validation_Report, with the MCP_Config file path, the field path of the offending value, and a message that names the violated rule, and SHALL exit with a non-zero status.
10. IF the MCP_Config references an environment variable through a Secret_Reference that the Env_Example_File does not list, THEN THE Config_Validator SHALL record an error in the Validation_Report that names the missing variable and the MCP_Server_Entry that references it.

### Requirement 9: Hook Configuration Parsing and Printing

**User Story:** As a template maintainer, I want the validator to parse and re-print hook files, so that I can check and normalize hook configuration reliably.

#### Acceptance Criteria

1. WHEN a Hook_File is provided that contains UTF-8 encoded valid JSON following the v1 hook schema, THE Hook_Config_Parser SHALL produce a Hook configuration object that contains one entry per Hook_Definition, in the same order as the `hooks` array in the file.
2. THE Hook_Config_Parser SHALL treat a Hook_File as following the v1 hook schema only if every one of these holds:
   - The top-level value is a JSON object.
   - The `version` field equals the string `"v1"`.
   - The `hooks` field is an array of 0 or more Hook_Definitions.
   - Every Hook_Definition has a non-empty string `name`, a `trigger` equal to one of the Hook_Trigger values, and an `action` object whose `type` is `command` or `agent`.
   - Every Hook_Definition whose `trigger` is a Matcher_Required_Trigger has a non-empty string `matcher` field.
   - Every Hook_Definition whose `trigger` is not a Matcher_Required_Trigger either omits the `matcher` field or has a string `matcher` field.
3. IF a Hook_File contains invalid JSON, including an empty file, THEN THE Hook_Config_Parser SHALL return an error that includes the file path and the 1-based line and column of the parse failure, and SHALL NOT produce a Hook configuration object.
4. IF a Hook_File contains valid JSON that violates the v1 hook schema, THEN THE Hook_Config_Parser SHALL return a single error that lists every violation in the file. Each violation SHALL include the file path and the field path of the violating field (for example `hooks[2].trigger`), and the Hook_Config_Parser SHALL NOT produce a Hook configuration object.
5. IF a Hook_File does not exist or cannot be read, THEN THE Hook_Config_Parser SHALL return an error that includes the file path and indicates that the file could not be read, and SHALL NOT produce a Hook configuration object.
6. WHEN a Hook configuration object is given to the Hook_Config_Printer, THE Hook_Config_Printer SHALL output UTF-8 JSON that follows the v1 hook schema. The output SHALL use 2-space indentation and LF line endings and SHALL end with exactly one trailing newline.
7. WHEN the Hook_Config_Printer outputs a Hook configuration object, THE Hook_Config_Printer SHALL write keys in a fixed order: `version` then `hooks` at the top level, and `name`, `trigger`, `matcher` (only when present in the Hook_Definition), `action` within each Hook_Definition. Hook_Definitions SHALL appear in the same order as in the Hook configuration object.
8. THE Hook_Config_Parser and Hook_Config_Printer SHALL satisfy the round-trip property: for every valid Hook configuration object, printing it with the Hook_Config_Printer and then parsing the output with the Hook_Config_Parser SHALL produce an equivalent object. Two objects are equivalent when they have the same `version`, the same number of Hook_Definitions in the same order, equal values for every field of every Hook_Definition, and the same presence or absence of the optional `matcher` field in every Hook_Definition.
9. THE Hook_Config_Printer SHALL satisfy the idempotence property: for every valid Hook_File, parsing it and printing the result (output A), then parsing output A and printing again (output B), SHALL give an output B that is byte-for-byte identical to output A.

### Requirement 10: Configuration Validation

**User Story:** As a template maintainer, I want a validation script for the template's own configuration, so that broken or unsafe configuration is caught before it is committed.

#### Acceptance Criteria

1. WHEN the Config_Validator runs, THE Config_Validator SHALL check every Markdown file in `.kiro/steering/`, every JSON file in `.kiro/hooks/`, and the MCP_Config, SHALL scan every version-controlled text file in the Template other than the Template_README for Placeholders as defined in Requirement 13 criterion 9, and SHALL report all errors and warnings found across all files in a single run instead of stopping at the first error.
2. IF a Steering_File has no YAML front matter, has front matter without an Inclusion_Mode field, or has an Inclusion_Mode value other than `always`, `fileMatch`, `manual`, or `auto`, THEN THE Config_Validator SHALL report an error naming the file path and the field path.
3. IF a Steering_File has Inclusion_Mode `fileMatch` and the File_Match_Pattern is absent or an empty string, THEN THE Config_Validator SHALL report an error naming the file path.
4. IF a Hook_Definition has a `trigger` value that is not one of the 13 allowed Hook_Trigger values, THEN THE Config_Validator SHALL report an error naming the file path and the Hook_Definition name.
5. IF a `command` Hook_Action references a Hook_Script path, resolved relative to the workspace root, that does not exist or does not have the executable permission set, THEN THE Config_Validator SHALL report an error naming the file path of the Hook_File and the unresolved script path.
6. IF a value in the MCP_Config, a Hook_File, or a Steering_File matches a pattern from the secret pattern list kept in the Config_Validator's configuration, and the value is not a Secret_Reference, THEN THE Config_Validator SHALL report an error naming the file path and the field path, and SHALL show at most the first 4 characters of the matched value, with every remaining character replaced by a mask character.
7. IF an MCP_Server_Entry has no `disabled` field, or its `disabled` field holds a non-boolean value, THEN THE Config_Validator SHALL report an error naming the server.
8. IF an MCP_Server_Entry `autoApprove` list contains a tool name that is not on the read-only allowlist kept in the Config_Validator's configuration, THEN THE Config_Validator SHALL report a warning naming the server and the tool.
9. WHEN the Config_Validator finishes a run with one or more errors, THE Config_Validator SHALL exit with code 1 and print the Validation_Report, which lists every error and warning with its severity, file path, field path, and message.
10. WHEN the Config_Validator finishes a run with zero errors, THE Config_Validator SHALL exit with code 0, print every warning found, and print a summary that gives the number of files checked and the number of warnings.
11. THE Config_Validator SHALL run with no network access and no dependencies beyond the runtime declared in `tech.md`, and SHALL complete a full run, including the Placeholder scan from criterion 1, within 10 seconds over 200 or fewer configuration files and 1,000 or fewer scanned text files.
12. IF a Hook_File or the MCP_Config is not valid JSON, or a Steering_File's front matter is not valid YAML, THEN THE Config_Validator SHALL report an error naming the file path, skip the remaining checks for that file, and continue checking the other files.
13. IF a Hook_File has a `version` value other than `"v1"`, a Hook_Definition is missing any of the `name`, `trigger`, or `action` fields, or a Hook_Definition whose `trigger` is a Matcher_Required_Trigger is missing the `matcher` field, THEN THE Config_Validator SHALL report an error naming the file path and the field path of each missing or invalid field.
14. IF the MCP_Config file does not exist at `.kiro/settings/mcp.json`, THEN THE Config_Validator SHALL report an error naming the expected file path.

### Requirement 11: Hook Script Tests

**User Story:** As a template maintainer, I want automated tests for the hook scripts, so that changes to guard logic do not silently weaken safety checks.

#### Acceptance Criteria

1. THE Template SHALL provide tests that read the Destructive_Command_List at test run time and, for every entry in it, run the Destructive_Command_Guard with hook context JSON on standard input describing a shell tool call containing that entry, and assert exit code 2. Because the list is read at run time, an entry added to the list is tested without any change to the tests.
2. THE Template SHALL provide tests that run the Destructive_Command_Guard against at least 10 safe commands, passed as hook context JSON on standard input, and assert exit code 0 for each. The safe commands SHALL include at least 3 that look like Destructive_Command_List entries but do not match them (for example `rm -rf ./build`, `git push` without `--force`, and `git reset --soft`).
3. THE Template SHALL provide tests that run the Risky_Tool_Guard, with hook context JSON on standard input, against at least one matching tool call for every entry in the Risky_Tool_List. Each test SHALL assert exit code 0 and standard output that parses as JSON with `permissionDecision` equal to `"ask"`.
4. THE Template SHALL provide tests that run the Risky_Tool_Guard against at least 5 tool calls that match no entry in the Risky_Tool_List. Each test SHALL assert exit code 0 and standard output that contains no `permissionDecision` value of `"ask"`.
5. THE Template SHALL provide a single command in `scripts/` that runs the Config_Validator and all hook script tests in one invocation, and that runs every test even when an earlier test fails.
6. WHEN the single test command completes and the Config_Validator reports zero errors and every hook script test passes, THE Template's test command SHALL exit with code 0 and print a summary with the number of tests passed.
7. IF the Config_Validator reports one or more errors or one or more hook script tests fail, THEN THE Template's test command SHALL exit with a non-zero code and print the name of each failing test and each Config_Validator error, along with the input given and the expected and actual result.
8. THE Template SHALL provide tests that run the Destructive_Command_Guard and the Risky_Tool_Guard with empty standard input and with standard input that is not valid JSON, and that assert the fail-closed behavior of each guard: the Destructive_Command_Guard exits with code 2 (Requirement 4 criterion 4), and the Risky_Tool_Guard exits with code 0 and writes standard output that parses as JSON with `permissionDecision` equal to `"ask"` (Requirement 5 criterion 6), so that neither guard silently allows a tool call when its input is malformed.

### Requirement 12: Example Spec

**User Story:** As a developer, I want an example spec, so that I can see the expected format of requirements, design, and tasks documents.

#### Acceptance Criteria

1. THE Example_Spec SHALL contain the three files `requirements.md`, `design.md`, and `tasks.md` in `.kiro/specs/example-feature/`, and each file SHALL contain at least one Markdown heading and at least one line of body text.
2. THE Example_Spec `requirements.md` SHALL write every acceptance criterion in exactly one of the six EARS patterns (Ubiquitous, Event-driven, State-driven, Unwanted event, Optional feature, Complex), and every system name used in an acceptance criterion SHALL be defined in the Glossary section of the same `requirements.md`.
3. THE Example_Spec `tasks.md` SHALL list each task as a Markdown checkbox item, and each task SHALL reference at least one requirement number that exists in the Example_Spec `requirements.md`.
4. THE Example_Spec `requirements.md` SHALL contain an Introduction section, a Glossary section, and at least 2 numbered requirements, and each requirement SHALL have a user story in the form "As a [role], I want [feature], so that [benefit]" followed by at least 2 numbered acceptance criteria.
5. THE Example_Spec `design.md` SHALL contain the sections Overview, Architecture, Components and Interfaces, Data Models, Error Handling, and Testing Strategy.
6. THE Example_Spec `tasks.md` SHALL reference every requirement number defined in the Example_Spec `requirements.md` in at least one task.

### Requirement 13: Documentation

**User Story:** As a developer adopting the template, I want clear documentation, so that I can set up, customize, and verify the harness in a new project.

#### Acceptance Criteria

1. THE Template_README SHALL contain one entry for each directory listed in Requirement 1, and each entry SHALL give the directory path and at least one sentence that states what files the directory holds and which harness part (steering, hooks, MCP configuration, specs, scripts, or documentation) those files configure.
2. THE Template_README SHALL give the setup steps as a numbered list in this order: (1) copy the Template into the target repository, (2) copy `.env.example` to `.env`, (3) replace every `{{PLACEHOLDER_NAME}}` value and every placeholder value in `.env`, (4) set `disabled` to `false` for each MCP_Server_Entry the developer wants to use, and (5) run the single command from Requirement 11 criterion 5. Each step that requires a shell command SHALL show that command as a copyable code block.
3. THE Template_README SHALL state that `.env` must not be committed and SHALL state the expected result of setup step 5: exit code 0 and a summary with the count of files checked, as defined in Requirement 10 criterion 10.
4. THE Customization_Guide SHALL contain one section for each of the four Inclusion_Mode values (`always`, `fileMatch`, `manual`, `auto`), and each section SHALL include one complete example Steering_File with front matter. The `fileMatch` example SHALL include a File_Match_Pattern, and the `auto` example SHALL include the `name` and `description` fields.
5. THE Customization_Guide SHALL explain how to add a Hook_Definition with one complete example Hook_File that contains the `name`, `trigger`, `matcher`, and `action` fields. The explanation SHALL list the allowed Hook_Trigger values, include an example of the stdin JSON input a Hook_Script receives, state that exit code 0 allows the action and exit code 2 blocks it, and show an example `permissionDecision` output for a `PreToolUse` hook.
6. THE Customization_Guide SHALL explain how to add an MCP_Server_Entry with one complete example entry that uses a Secret_Reference in `env` instead of a literal secret value, pins the server package to an exact version instead of a range or `latest` tag, and sets `disabled` to `true`. The explanation SHALL also state that any variable named in a Secret_Reference must be added to the Env_Example_File.
7. THE Customization_Guide SHALL explain how to add and remove entries in the Destructive_Command_List and the Risky_Tool_List. For each list, it SHALL give the file location, one example of adding an entry, and one example of removing an entry, and it SHALL state that the tests from Requirement 11 must be run after any change to either list.
8. THE Template_README SHALL list every `{{PLACEHOLDER_NAME}}` that appears in any file of the Template. Each list item SHALL give the placeholder name, the path of each file that contains it, and a one-line description of the value to supply.
9. IF a text file in the Template, other than the Template_README itself, contains a Placeholder whose name does not appear in the Template_README placeholder list, THEN THE Config_Validator SHALL report an error in the Validation_Report naming the Placeholder and the path of each file that contains the Placeholder.
10. THE Template_README and the Customization_Guide SHALL contain no literal secret values. Every credential shown in an example SHALL use a Secret_Reference or a placeholder value that matches no pattern in the Config_Validator secret pattern list.
11. WHEN an example Steering_File, Hook_File, or MCP_Server_Entry from the Customization_Guide is copied into the matching Template location and the Config_Validator runs, THE Config_Validator SHALL report zero errors for that example.
