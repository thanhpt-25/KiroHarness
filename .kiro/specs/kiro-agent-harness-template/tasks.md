# Implementation Plan: Kiro Agent Harness Template

## Overview

The implementation uses Python 3.10+ (standard library only) for the Config_Validator and hook logic, with thin POSIX `sh` wrappers as Hook_Scripts, as decided in the design. Hypothesis is a pinned dev-only dependency used only by `tests/property/`.

The order is: pure validator building blocks (Hook_Config_Parser/Printer, report, front matter, steering, hook rules, MCP checks), then the hook library and Hook_Scripts, then the shipped Template content, then the validator entry point that ties every checker together, then the hook script tests and the Validation_Command, and finally the documentation. Each property test sits next to the code it checks.

## Tasks

- [x] 1. Set up the Template skeleton and test infrastructure
  - Create the directories from the design's Directory Layout: `.kiro/steering/`, `.kiro/hooks/`, `.kiro/hooks/examples/`, `.kiro/hooks/scripts/lib/`, `.kiro/settings/`, `.kiro/specs/example-feature/`, `scripts/harness_validator/`, `docs/`, `tests/hooks/`, `tests/validator/`, `tests/property/`, `tests/fixtures/`, `tests/integration/`
  - Write `.gitignore` so that `.env`, `.env.local`, `.env.production`, and `.kiro/settings/mcp.local.json` are ignored and `.env.example` and `.kiro/settings/mcp.json` are not; also ignore `.venv/`, `__pycache__/`, `.hypothesis/`
  - Write `requirements-dev.txt` with `hypothesis==<exact version>`
  - Create `scripts/harness_validator/__init__.py`, `tests/__init__.py` and package `__init__.py` files for each test directory
  - Write `tests/property/_profiles.py` registering a default Hypothesis profile (`max_examples=100, deadline=None`) and a `ci` profile (`max_examples=300`), selected by `HYPOTHESIS_PROFILE`
  - _Requirements: 1.1, 1.3, 10.11_

- [x] 2. Implement the Hook_Config_Parser and Hook_Config_Printer
  - [x] 2.1 Implement hook data models and the parser in `scripts/harness_validator/hookconfig.py`
    - Define `TRIGGERS`, `MATCHER_REQUIRED`, and frozen dataclasses `HookAction`, `HookDefinition`, `HookFile`, keeping unknown keys in sorted `extra` tuples
    - Define `HookReadError`, `HookParseError`, `HookSchemaError(path, violations)` where each violation is a `(field_path, message)` pair
    - Implement `parse_hook_file(path)` and `parse_hook_text(text, path)`: read bytes, report invalid UTF-8 with line and column, `json.loads` with an `object_pairs_hook` that rejects duplicate keys, 1-based line/column on parse failure (empty file reports line 1, column 1)
    - Collect every v1 schema violation into one `HookSchemaError`: non-object top level, `version` not `"v1"`, `hooks` not an array, empty or non-string `name`, trigger outside the 13 values (case-sensitive), action `type` not `command`/`agent`, missing or empty `matcher` on a Matcher_Required_Trigger, non-string `matcher` elsewhere
    - Accept `hooks` arrays with zero entries; Template-only rules live in `hook_rules.py`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [x] 2.2 Implement the Hook_Config_Printer in `scripts/harness_validator/hookconfig.py`
    - Implement `print_hook_file(hook_file)` using `json.dumps(indent=2, ensure_ascii=False)` over dictionaries built in the fixed key order: `version`, `hooks`; then `name`, `trigger`, `matcher` (only when not None), `action`, `timeout`, `description`, `enabled` (each only when not None), then sorted `extra` keys; action keys `type`, `command`, `prompt`, then sorted `extra`
    - Append exactly one `\n`; output contains LF line endings only
    - _Requirements: 9.6, 9.7, 9.8, 9.9_

  - [x] 2.3 Write hook strategies and property test for the round trip
    - Create `tests/property/strategies_hooks.py` with `hook_files()` (valid `HookFile` objects with and without `matcher`, optional fields, extra keys, non-ASCII and escape-heavy strings) and `hook_json_texts()` (valid documents with random whitespace, indentation, and key order)
    - Write `tests/property/test_p01_hook_roundtrip.py`
    - **Property 1: Hook configuration round trip**
    - **Validates: Requirements 9.1, 9.8**

  - [x] 2.4 Write property test for printer idempotence
    - `tests/property/test_p02_printer_idempotence.py`, using `hook_json_texts()`
    - **Property 2: Hook printer idempotence**
    - **Validates: Requirements 9.9**

  - [x] 2.5 Write property test for printer output format and key order
    - `tests/property/test_p03_printer_format.py`
    - **Property 3: Hook printer output format and key order**
    - **Validates: Requirements 9.6, 9.7**

  - [x] 2.6 Write property test for schema acceptance and complete violation listing
    - `tests/property/test_p04_parser_schema.py` with a local `schema_mutations()` catalog that records the field path each mutation breaks
    - **Property 4: Parser schema acceptance and complete violation listing**
    - **Validates: Requirements 9.2, 9.4**

  - [x] 2.7 Write property test for parse error positions
    - `tests/property/test_p05_parse_positions.py` covering truncation, stray-character insertion, and the empty file
    - **Property 5: Parse errors report a 1-based position**
    - **Validates: Requirements 9.3**

  - [x] 2.8 Write unit tests for parser read errors
    - `tests/validator/test_hookconfig.py`: missing file, unreadable file (permission removed), invalid UTF-8, duplicate keys
    - _Requirements: 9.3, 9.5_

- [x] 3. Implement report, placeholder, and secret helpers
  - [x] 3.1 Implement the Validation_Report in `scripts/harness_validator/report.py`
    - `Severity` enum, ordered frozen `Finding(severity, path, field, rule, message)`
    - `render(findings, files_checked)` sorts by path, field, rule; prints one line per finding with severity, path, field path, `[RULE]`, and message; prints `Summary: <n> files checked, <e> errors, <w> warnings`; returns exit code 1 if any error, else 0
    - _Requirements: 10.9, 10.10_

  - [x] 3.2 Write property test for report rendering and exit code
    - `tests/property/test_p26_report_render.py`
    - **Property 26: Report rendering and exit code**
    - **Validates: Requirements 10.9, 10.10**

  - [x] 3.3 Implement placeholder helpers in `scripts/harness_validator/placeholders.py`
    - `PLACEHOLDER_RE`, `find_placeholders(text)`
    - `readme_placeholder_list(readme_text)` parsing the `## Placeholders` section items of the form ``- `{{NAME}}` — <files> — <description>``
    - `tracked_text_files(root)` using `git ls-files -z` when available, else a filesystem walk skipping `.git/`, `node_modules/`, `.venv/`, and `.gitignore` matches, returning a flag that the fallback was used; a file is text when it has no NUL byte in the first 8 KiB and decodes as UTF-8
    - _Requirements: 2.7, 10.1, 13.8, 13.9_

  - [x] 3.4 Write property test for placeholder extraction
    - `tests/property/test_p27_placeholder_extract.py` with near-miss generators (lowercase, leading digit or underscore, 65-character names, single braces, inner spaces)
    - **Property 27: Placeholder extraction matches the placeholder format**
    - **Validates: Requirements 2.7**

  - [x] 3.5 Implement secret helpers and the validator configuration
    - Write `scripts/validator-config.json` with `secret_patterns`, `read_only_allowlist`, `known_mutating_tools`, and `mcp_minimum_versions` (`{"mcp-server-git": "2026.10.28"}`) exactly as in the design's Data Models
    - Implement `scripts/harness_validator/secrets.py`: `load_validator_config(path)`, `SecretPattern`, `SecretHit`, `find_secrets(value, patterns)` that ignores values fully matching `^\$\{[A-Z][A-Z0-9_]{0,63}\}$` and hits inside a `${...}` span, `mask(value)` keeping the first `min(4, len(v) // 2)` characters and replacing the rest with `*`, and `walk_json_strings(obj, prefix)` yielding `(field path, value)` pairs
    - _Requirements: 8.3, 10.6_

  - [x] 3.6 Write unit tests for the secret patterns
    - `tests/validator/test_secrets.py`: one positive sample per pattern id, Secret_References not reported, placeholder values such as `replace-me` not matched
    - _Requirements: 10.6, 13.10_

- [x] 4. Implement front matter parsing and steering checks
  - [x] 4.1 Implement the YAML front matter subset in `scripts/harness_validator/frontmatter.py`
    - `split_front_matter(text)` returning `(yaml_text, body)` or `None` when there is no `---` block
    - `parse_front_matter(yaml_text)` supporting `key: value` scalars (plain, single-quoted, double-quoted), booleans, flow sequences, block sequences, and `#` comments; raise `FrontMatterError(line, msg)` for any other construct (nested mappings, anchors, multi-line scalars, tab indentation) and for duplicate keys
    - `dump_front_matter(data)` that quotes strings needing it
    - _Requirements: 10.12_

  - [x] 4.2 Write property test for the front matter round trip
    - `tests/property/test_p09_frontmatter_roundtrip.py` with strings containing `:`, `#`, `{`, and leading spaces
    - **Property 9: Front matter round trip for the supported YAML subset**
    - **Validates: Requirements 10.12**

  - [x] 4.3 Implement minimatch-style glob matching in `scripts/harness_validator/globmatch.py`
    - `**/` matches zero or more segments, `*` and `?` do not match `/`, `{a,b}` alternatives; match against workspace-relative POSIX paths
    - _Requirements: 2.3, 2.4_

  - [x] 4.4 Write unit tests for glob matching
    - `tests/validator/test_globmatch.py` with every matching and non-matching example path from Requirements 2.3 and 2.4 against the design's `testing.md` and `coding-standards.md` patterns
    - _Requirements: 2.3, 2.4_

  - [x] 4.5 Implement steering checks in `scripts/harness_validator/steering.py`
    - `check_steering(path, text)` returning findings for STEER-FM (missing front matter, invalid YAML subset, `inclusion` missing, duplicated, or not one of the four values), STEER-FILEMATCH (absent or empty `fileMatchPattern`, or a list with an empty item), and STEER-AUTO (`name` outside 1 to 64 characters, `description` outside 1 to 200 characters)
    - A front matter parse failure produces one finding and skips the other checks for that file
    - _Requirements: 2.1, 2.6, 2.9, 2.10, 2.11, 10.2, 10.3, 10.12_

  - [x] 4.6 Write property test for steering front matter validation
    - `tests/property/test_p08_steering_validation.py` with lengths 0, 1, 64, 65, 200, 201 and case variants of `inclusion`
    - **Property 8: Steering front matter validation**
    - **Validates: Requirements 2.6, 2.9, 2.10, 2.11, 10.2, 10.3**

- [x] 5. Implement Template hook rules
  - [x] 5.1 Implement `scripts/harness_validator/hook_rules.py`
    - `check_hook_file(path, text, root)`: run the parser; map `HookParseError` to one HOOK-JSON finding and `HookSchemaError` to one HOOK-SCHEMA finding per violation (trigger errors include the Hook_Definition name), then skip the remaining checks when parsing failed
    - HOOK-ID: file name stem matches `^[a-z0-9]+(-[a-z0-9]+)*$` and is at most 64 characters
    - HOOK-RULES: empty `hooks`, duplicate or over-64 names, missing or empty `command`, `timeout` not an integer 1 to 300 (booleans and floats rejected), empty `prompt`, matcher that does not compile with `re.compile`
    - HOOK-WILDCARD warning for matchers containing `*` or `?`
    - HOOK-SCRIPT: resolve the first token ending in `.sh` (after optional `sh`/`bash`) relative to `root`; error when missing or lacking the owner execute bit, naming the Hook_File and script path
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 10.4, 10.5, 10.13_

  - [x] 5.2 Write unit tests for hook rules
    - `tests/validator/test_hook_rules.py`: HOOK-SCRIPT missing and non-executable script, HOOK-WILDCARD warning, HOOK-ID boundary names (leading dash, double dash, 64 and 65 characters), boolean `timeout`
    - _Requirements: 3.1, 3.4, 10.5_

- [x] 6. Implement MCP_Config checks
  - [x] 6.1 Implement `.env.example` parsing in `scripts/harness_validator/envfile.py`
    - `parse_env_example(text)` returning an `EnvExample` with each variable, its line numbers, and the comment lines directly above it
    - _Requirements: 8.6_

  - [x] 6.2 Implement `scripts/harness_validator/mcp.py`
    - `check_mcp(path, text, env_example, config)`: MCP-JSON on parse failure (then skip), MCP-DISABLED, MCP-PIN (package spec in `args[0]` or after `--from` must be `<name>@X.Y.Z`; version compared numerically against `mcp_minimum_versions`), MCP-SECRET-REF for credential-like `env` keys, MCP-AUTOAPPROVE (known-mutating list or mutating verb regex) as error, MCP-AUTOAPPROVE-UNKNOWN as warning, MCP-GIT-SCOPE (`--repository` followed by `.` or an absolute path, no `..`), MCP-ENV-EXAMPLE (missing, duplicated, or no comment naming the server)
    - Every finding carries the MCP_Config path and a field path such as `mcpServers.git.args[0]`
    - _Requirements: 8.2, 8.3, 8.4, 8.5, 8.6, 8.8, 8.9, 8.10, 10.7, 10.8, 10.12_

  - [x] 6.3 Write property test for credential Secret_References
    - `tests/property/test_p20_mcp_secret_refs.py`
    - **Property 20: Credential values in MCP env must be Secret_References**
    - **Validates: Requirements 8.3**

  - [x] 6.4 Write property test for uvx version pinning
    - `tests/property/test_p21_mcp_pinning.py`
    - **Property 21: uvx packages must be pinned to an exact version**
    - **Validates: Requirements 8.4**

  - [x] 6.5 Write property test for autoApprove classification
    - `tests/property/test_p22_autoapprove.py`
    - **Property 22: autoApprove classification**
    - **Validates: Requirements 8.5, 10.8**

  - [x] 6.6 Write property test for `.env.example` coverage
    - `tests/property/test_p23_env_example.py`
    - **Property 23: Env example covers every Secret_Reference**
    - **Validates: Requirements 8.6, 8.10**

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement the guard Hook_Scripts
  - [x] 8.1 Implement hook input handling in `.kiro/hooks/scripts/lib/hookio.py`
    - `HookInput`, `HookInputError`, `read_hook_input(stream, max_bytes=1_048_576)` accepting `tool_name`/`toolName` and `tool_input`/`toolArgs`, decoding a JSON-string `tool_input` once, and raising on empty input, invalid UTF-8, invalid JSON, or a non-object top level
    - `workspace_root()` two levels above `.kiro/hooks/scripts/`
    - _Requirements: 4.4, 5.6_

  - [x] 8.2 Implement the Destructive_Command_Guard
    - Write `.kiro/hooks/scripts/lib/destructive_guard.py` with `Pattern`, `ListLoadError`, `load_patterns`, `normalize`, `split_segments` (on `&&`, `||`, `;`, `|`, newline, ignoring quotes), `tokenize`, `match_segment` (in-order token subsequence), `check`, and `main` following the design's exit-code table; load the list before reading stdin; exit 0 for `control_bash_process` with `action == "stop"`
    - Write `.kiro/hooks/scripts/destructive-commands.txt` with the header comment and the default entries listed in the design
    - Write `.kiro/hooks/scripts/destructive-guard.sh` (`#!/bin/sh`, locate root, `command -v python3` check that exits 2 with `destructive-command-guard: python3 not found; blocking`, `exec python3 -I`); set the executable bit and record mode 100755 with `git update-index --chmod=+x` when in a git repository
    - _Requirements: 1.4, 1.5, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8_

  - [x] 8.3 Write property test for the destructive guard against a reference matcher
    - `tests/property/test_p10_destructive_reference.py` with a small token alphabet, random case and whitespace, and an independent plain-loop reference implementation
    - **Property 10: Destructive guard agrees with the reference matcher**
    - **Validates: Requirements 4.2, 4.3**

  - [x] 8.4 Write property test for chained commands
    - `tests/property/test_p11_chained_commands.py`
    - **Property 11: Chained commands block if any segment blocks**
    - **Validates: Requirements 4.6**

  - [x] 8.5 Write property test for fail-closed input handling
    - `tests/property/test_p12_destructive_fail_closed.py`
    - **Property 12: Destructive guard fails closed on malformed input**
    - **Validates: Requirements 4.4, 11.8**

  - [x] 8.6 Write property test for destructive list loading
    - `tests/property/test_p13_destructive_list_load.py` covering 0, 1, 200, and 201 patterns with interleaved blank and comment lines
    - **Property 13: Destructive list loading**
    - **Validates: Requirements 4.5, 4.8**

  - [x] 8.7 Implement the Risky_Tool_Guard
    - Write `.kiro/hooks/scripts/lib/risky_guard.py` with `AnyArgs`, `RegexArg`, `HostNotIn`, `RiskyEntry`, `RiskyListError`, `parse_list` (split on the first two ` | `, report line numbers, compile regexes), `matches` (`re.search` on the stringified field; `urlsplit` for `host-not-in`, treating unparseable, hostless, or non-http(s) URLs as not allowed; subdomains of allowed hosts are allowed), `decide`, `ask_json`, and `main` (always exit 0) following the design's table
    - Write `.kiro/hooks/scripts/risky-tools.conf` with the default entries from the design, each preceded by an `# example: <json tool_input>` comment
    - Write `.kiro/hooks/scripts/risky-tool-guard.sh` whose missing-`python3` branch prints the `"ask"` JSON with `printf`; set the executable bit and record mode 100755
    - _Requirements: 1.4, 1.5, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8_

  - [x] 8.8 Write property test for the risky guard against a reference decision
    - `tests/property/test_p14_risky_reference.py` with a local `risky_lists()` strategy and an independent reference predicate
    - **Property 14: Risky guard agrees with the reference decision**
    - **Validates: Requirements 5.2, 5.3, 5.5**

  - [x] 8.9 Write property test for unusable input and configuration
    - `tests/property/test_p15_risky_fail_ask.py`
    - **Property 15: Risky guard asks when input or configuration is unusable**
    - **Validates: Requirements 5.6, 5.7, 11.8**

- [x] 9. Implement the quality and lifecycle Hook_Scripts
  - [x] 9.1 Implement the process runner in `.kiro/hooks/scripts/lib/runner.py`
    - `RunResult`, `run_with_deadline(argv, deadline, env)` using `start_new_session=True`, SIGTERM to the process group at the deadline, then SIGKILL after 2 seconds; `tail_lines(text, n=200)` handling `\n` and `\r\n`
    - _Requirements: 6.6, 6.7, 7.3_

  - [x] 9.2 Implement the Lint_Command and Test_Command scripts
    - Write `scripts/project-commands.env` with `LINT_FILE_COMMAND`, `TEST_FILE_COMMAND`, and `TEST_COMMAND` placeholder values (`KEY="value"` lines only)
    - Write `scripts/lint.sh <file>` and `scripts/test.sh [<file>]`: source the env file, exit 3 with `not configured: <KEY>` when empty or still a placeholder, otherwise run `sh -c "$CMD \"\$1\"" lint "$file"` so the path is a positional argument; `#!/bin/sh`, executable bit, mode 100755
    - _Requirements: 1.4, 1.5, 6.2, 6.3, 6.4_

  - [x] 9.3 Implement the Quality_Hook script
    - Write `.kiro/hooks/scripts/lib/quality.py` with `load_commands`, `is_configured`, `saved_path` (first non-empty of `file_path`, `path`, `tool_input.path`, `tool_input.file_path`, `files[0]`, made workspace-relative), and `main`: lint every saved path, test only when it matches `TEST_FILE_REGEX`, `CI=true` in the environment, one 110-second deadline shared across both commands, messages and exit codes as in the design's output table, failure messages written to both stdout and stderr
    - Write `.kiro/hooks/scripts/quality-hook.conf` with the default `TEST_FILE_REGEX`
    - Write `.kiro/hooks/scripts/quality-on-save.sh` wrapper; executable bit, mode 100755
    - _Requirements: 1.4, 1.5, 6.2, 6.3, 6.4, 6.6, 6.7, 6.8_

  - [x] 9.4 Write property test for passing only the saved path
    - `tests/property/test_p16_quality_saved_path.py` running the real script against stub lint/test commands that record their argv and environment, with paths containing spaces, quotes, `$`, `;`, and backticks
    - **Property 16: Quality hook passes only the saved path**
    - **Validates: Requirements 6.2, 6.3**

  - [x] 9.5 Write property test for the command configuration predicate
    - `tests/property/test_p17_is_configured.py`
    - **Property 17: Command configuration predicate**
    - **Validates: Requirements 6.4**

  - [x] 9.6 Write property test for output truncation
    - `tests/property/test_p18_tail_lines.py`
    - **Property 18: Output truncation keeps the last 200 lines**
    - **Validates: Requirements 6.6**

  - [x] 9.7 Implement the SessionStart script
    - Write `.kiro/hooks/scripts/lib/session_info.py` (git branch or detached HEAD short sha, uncommitted file count from `git status --porcelain=v1 --untracked-files=all`, 4-second timeout per call, `Git information unavailable: <reason>` fallback, always exit 0)
    - Write `.kiro/hooks/scripts/session-start.sh`; executable bit, mode 100755
    - _Requirements: 1.4, 1.5, 7.1, 7.6_

  - [x] 9.8 Implement the UserPromptSubmit secret scan
    - Write `.kiro/hooks/scripts/lib/prompt_scan.py` loading `secret_patterns` from `scripts/validator-config.json`; exit 2 with the pattern id and without the matched value on a match; exit 0 with empty stderr for no match, an empty prompt, or a missing `prompt`; exit 2 naming the file when the pattern file cannot be loaded
    - Write `.kiro/hooks/scripts/prompt-secret-scan.sh`; executable bit, mode 100755
    - _Requirements: 1.4, 1.5, 7.2, 7.7_

  - [x] 9.9 Write property test for the prompt secret scan
    - `tests/property/test_p19_prompt_scan.py` with one `secret_values(pattern_id)` strategy per secret pattern
    - **Property 19: Prompt secret scan blocks exactly the prompts with secrets**
    - **Validates: Requirements 7.2, 7.7**

  - [x] 9.10 Implement the PostTaskExec script
    - Write `.kiro/hooks/scripts/post-task-tests.sh` and `.kiro/hooks/scripts/lib/post_task.py`: run `scripts/test.sh` with no file argument through `run_with_deadline` with `CI=true` and a 290-second deadline; exit 0 on pass, exit 2 with the last 200 output lines on stderr on failure or timeout, exit 0 with the not-configured message when `TEST_COMMAND` is a placeholder or empty; executable bit, mode 100755
    - _Requirements: 1.4, 1.5, 7.3, 7.8_

- [x] 10. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 11. Create the shipped Template content and the Config_Validator entry point
  - [x] 11.1 Write the Hook_Files
    - Write `.kiro/hooks/destructive-command-guard.json`, `risky-tool-guard.json` (matcher an anchored alternation of every tool in `risky-tools.conf`), `quality-on-save.json`, `session-start-context.json`, `prompt-secret-scan.json`, `post-task-tests.json`, `stop-validate.json` with the triggers, matchers, commands, timeouts, and Stop prompt from the design's Hook Files table
    - Write `.kiro/hooks/examples/new-file-reminder.json` and `.kiro/hooks/examples/pre-compact-snapshot.json` with `"enabled": false`; for the pre-compact example, add any script it runs under `.kiro/hooks/scripts/` with an executable bit
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 4.1, 5.1, 6.1, 6.5, 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 11.2 Write the Steering_Files
    - Write `product.md`, `tech.md`, `structure.md`, `security.md` (`inclusion: always`), `testing.md` and `coding-standards.md` (`fileMatch` with the design's patterns), `release-checklist.md` (`manual`), and `api-design.md` (`auto` with `name` and `description`) in `.kiro/steering/`
    - `security.md` has the four `##` headings from the design; `tech.md` declares Python 3.10+ and POSIX `sh`, the minimum supported Kiro IDE version, and the date the MCP pins were checked; project-specific values use `{{PLACEHOLDER_NAME}}` placeholders
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 10.11_

  - [ ] 11.3 Write the MCP_Config and Env_Example_File
    - Write `.kiro/settings/mcp.json` with the `aws-docs`, `fetch`, and `git` entries from the design (re-check versions on PyPI first; keep the git pin at or above 2026.10.28)
    - Write `.env.example` documenting the format with placeholder values that match no secret pattern, listing every variable referenced by the shipped `mcp.json`
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8_

  - [x] 11.4 Write the Example_Spec
    - Write `.kiro/specs/example-feature/requirements.md` (Introduction, Glossary, at least 2 requirements with user stories and at least 2 EARS acceptance criteria each), `design.md` (Overview, Architecture, Components and Interfaces, Data Models, Error Handling, Testing Strategy), and `tasks.md` (checkbox tasks referencing every requirement number)
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6_

  - [x] 11.5 Implement the Config_Validator entry point
    - Write `scripts/harness_validator/__main__.py` with `--root`: discover Markdown files in `.kiro/steering/`, JSON files directly in `.kiro/hooks/` and `.kiro/hooks/examples/`, and the MCP_Config; run steering, hook, MCP, and secret checks (SECRET findings with masked values for MCP_Config, Hook_Files, and Steering_Files)
    - Add cross-file checks: MCP-MISSING, DESTR-LIST (via `load_patterns`), RISKY-LIST (via `parse_list`, plus the `# example:` comment check), RISKY-COVER (every listed tool fully matches the Risky_Tool_Guard matcher); load the guard modules from `.kiro/hooks/scripts/lib/` with `importlib` so parsing logic is shared
    - Add the placeholder scan: one PLACEHOLDER error per unlisted name listing every file, PLACEHOLDER-STALE warnings, and a warning when the filesystem fallback was used
    - Wrap each checker so an exception becomes an `[INTERNAL] <checker> crashed: <exception>` error for that file and the run continues; exit 2 with a traceback only on a crash outside the checkers
    - Write `scripts/validate-config.sh` running `python3 -I -m harness_validator --root <workspace>` with `scripts/` on the module path; `#!/bin/sh`, executable bit, mode 100755
    - _Requirements: 1.4, 1.5, 3.8, 3.9, 4.5, 5.1, 5.7, 10.1, 10.5, 10.6, 10.9, 10.10, 10.11, 10.12, 10.14, 11.3, 13.9_

- [x] 12. Test the Config_Validator end to end
  - [x] 12.1 Write property test for hook rule violations
    - `tests/property/test_p06_hook_rule_violations.py` with a `rule_mutations()` catalog, running the validator over a temporary Template copy
    - **Property 6: Every hook rule violation is reported with its field path**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 10.4, 10.13**

  - [x] 12.2 Write property test for continuing past parse failures
    - `tests/property/test_p07_continue_after_parse_errors.py`
    - **Property 7: Validation reports all files and continues past parse failures**
    - **Validates: Requirements 3.9, 10.1, 10.12**

  - [x] 12.3 Write property test for MCP violation reporting
    - `tests/property/test_p24_mcp_violations.py`
    - **Property 24: Every MCP violation is reported**
    - **Validates: Requirements 8.9, 10.7**

  - [x] 12.4 Write property test for secret masking and Secret_Reference exclusion
    - `tests/property/test_p25_secret_masking.py`
    - **Property 25: Secret findings are masked and Secret_References are ignored**
    - **Validates: Requirements 10.6**

  - [x] 12.5 Write property test for unlisted placeholders
    - `tests/property/test_p28_unlisted_placeholders.py` with an independent reference implementation
    - **Property 28: Unlisted placeholders are reported with every file**
    - **Validates: Requirements 13.9**

  - [x] 12.6 Write unit tests for the validator entry point
    - `tests/validator/test_validator_main.py`: missing `mcp.json` (MCP-MISSING), RISKY-COVER failure, a crashing checker produces `[INTERNAL]` and the run continues, every import in `harness_validator` is in `sys.stdlib_module_names`, and a full run over a generated workspace of 200 configuration files and 1,000 text files finishes within 10 seconds
    - _Requirements: 5.1, 10.1, 10.11, 10.14_

- [x] 13. Implement the hook script tests and the Validation_Command
  - [x] 13.1 Write Destructive_Command_Guard tests in `tests/hooks/test_destructive_guard.py`
    - Read `destructive-commands.txt` at run time and run the real script once per entry with shell-tool hook JSON on stdin, asserting exit 2 and the pattern on stderr
    - Run at least 10 safe commands, including `rm -rf ./build`, `git push origin main`, and `git reset --soft HEAD~1`, asserting exit 0 and empty stderr
    - Empty stdin and `not json` assert exit 2; a `control_bash_process` stop call asserts exit 0; a missing list asserts exit 2 naming the path; a 10,000-character command against 200 patterns finishes within 2 seconds
    - _Requirements: 4.4, 4.7, 4.8, 11.1, 11.2, 11.8_

  - [x] 13.2 Write Risky_Tool_Guard tests in `tests/hooks/test_risky_guard.py`
    - Read `risky-tools.conf` at run time and use each entry's `# example:` comment as a matching call, asserting exit 0 and JSON stdout with `permissionDecision` `"ask"` that names the tool and entry
    - Run at least 5 non-matching tool calls asserting no `"ask"` output; empty stdin and `not json` assert exit 0 with `"ask"`; a malformed list asserts `"ask"` naming the file
    - Meta-test: a temporary list with one extra entry grows the number of generated cases by one; each check finishes within 2 seconds
    - _Requirements: 5.2, 5.3, 5.5, 5.6, 5.7, 5.8, 11.3, 11.4, 11.8_

  - [x] 13.3 Write tests for the quality and lifecycle hooks
    - `tests/hooks/test_quality_and_lifecycle.py`: Quality_Hook not configured, pass, failure with truncated output, and timeout (using stub commands and a shortened deadline); SessionStart in a temporary repository, a non-repository directory, and with `git` removed from `PATH`; PostTaskExec pass, failure, and not configured; prompt scan with a pattern file that cannot be loaded
    - _Requirements: 6.4, 6.6, 6.7, 6.8, 7.1, 7.3, 7.6, 7.8_

  - [x] 13.4 Implement the Validation_Command
    - Write `tests/_result.py` with a `unittest` result class that prints, for each failure, the test name, the input, and the expected and actual result
    - Write `scripts/validate.sh`: run `scripts/validate-config.sh` and capture its report and exit code, run `python3 -I -m unittest discover` over `tests/hooks` and `tests/validator` with the custom result class so every test runs, print `Validation: <n> files checked, <w> warnings; Tests: <passed> passed, <failed> failed`, and exit 0 only when the validator exited 0 and no test failed or errored; `#!/bin/sh`, executable bit, mode 100755
    - _Requirements: 1.4, 1.5, 11.5, 11.6, 11.7_

  - [x] 13.5 Implement the property test and MCP update scripts
    - Write `scripts/test-properties.sh` running `tests/property` with `uv run --with-requirements requirements-dev.txt`, falling back to a local virtualenv
    - Write `scripts/check-mcp-updates.sh` that reads `mcp.json`, queries `https://pypi.org/pypi/<package>/json`, and prints pinned versus latest without changing files
    - Both start with `#!/bin/sh`, have the executable bit, and are recorded as mode 100755
    - _Requirements: 1.4, 1.5, 8.4_

  - [x] 13.6 Write tests for the Validation_Command
    - `tests/validator/test_validate_command.py`: a fixture suite with one failing test and one validator error, asserting a non-zero exit, that every test ran, and that the failure details and validator error were printed; a clean fixture asserts exit 0 and the summary
    - _Requirements: 11.5, 11.6, 11.7_

- [x] 14. Write the documentation and its tests
  - [x] 14.1 Write `README.md`
    - Directory table for every directory in Requirement 1, numbered setup steps in the required order with copyable code blocks, the `.env` must-not-be-committed warning, the expected step-5 output, a `## Placeholders` section listing every placeholder with its files and description (including `{{PLACEHOLDER_NAME}}` marked "nothing to replace"), and pointers to `scripts/test-properties.sh` and `scripts/check-mcp-updates.sh`
    - _Requirements: 13.1, 13.2, 13.3, 13.8, 13.10_

  - [x] 14.2 Write `docs/CUSTOMIZING.md`
    - One section per Inclusion_Mode with a complete example Steering_File; adding a hook (trigger list, stdin example, exit-code meaning, `permissionDecision` example, a complete Hook_File); adding an MCP server (disabled entry with `${EXAMPLE_SERVICE_TOKEN}`, exact pin, `.env.example` rule); editing both guard lists with add and remove examples and the instruction to run the tests; enabling the example hooks; the quality hook extension list; the supported YAML subset; tool name maintenance; MCP version updates with the optional Renovate example; the optional CI workflow example; the manual integration checklist
    - Fence every validatable example with an info string such as `json example=hook path=.kiro/hooks/my-hook.json`
    - _Requirements: 6.1, 7.5, 13.4, 13.5, 13.6, 13.7, 13.10_

  - [x] 14.3 Write the documentation example test
    - `tests/validator/test_docs_examples.py`: extract each `example=` block from `docs/CUSTOMIZING.md`, copy it into a temporary Template copy at its `path`, run the validator, and assert zero errors
    - _Requirements: 13.11_

  - [x] 14.4 Write Template content smoke tests
    - `tests/validator/test_template_content.py`: required directories and non-empty files, `git check-ignore` results in a temporary repository, execute bits and git mode 100755, shebangs, steering inclusion values and glob examples, `security.md` headings, shipped hook matchers and timeouts, the Stop prompt, shipped MCP content, Example_Spec structure and requirement references, README and Customization_Guide content, and no secret pattern matches in the docs
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 2.5, 2.8, 4.1, 5.1, 6.1, 6.5, 7.4, 8.1, 8.2, 8.7, 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7, 13.8, 13.10_

  - [x] 14.5 Write MCP integration tests
    - `tests/integration/test_mcp_servers.py`, skipped unless `HARNESS_INTEGRATION=1`: start each pinned server through `uvx`, list its tools, confirm every `autoApprove` name exists, and confirm the git server's `git_status` reports the workspace repository
    - _Requirements: 8.1, 8.5, 8.8_

- [ ] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP. The guard tests in 13.1 and 13.2 and the Validation_Command in 13.4 are not optional, because Requirement 11 makes them part of the Template.
- Each property test file carries the tag `# Feature: kiro-agent-harness-template, Property <N>: <title>` and uses the profiles from `tests/property/_profiles.py`.
- The design lists known gaps that depart from the literal requirements: `control_bash_process` stop calls exit 0 (Requirement 4.4), three-tier autoApprove severity (Requirements 8.9 and 10.8), printer order for `timeout` and other optional keys (Requirement 9.7), validator hook scope limited to `.kiro/hooks/` and `.kiro/hooks/examples/` (Requirement 10.1), and git server confinement through `--repository .` (Requirement 8.8). The tasks implement the design's choices; confirm them or update `requirements.md`.
- The saved-file path field for `PostFileSave` and the `"ask"` blocking contract need confirmation on a real Kiro build; the checklist is in `docs/CUSTOMIZING.md` (task 14.2).

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1"] },
    { "id": 1, "tasks": ["2.1", "3.1", "3.3", "3.5", "4.1", "4.3", "6.1"] },
    { "id": 2, "tasks": ["2.2", "3.2", "3.4", "3.6", "4.2", "4.4", "4.5", "5.1", "6.2"] },
    { "id": 3, "tasks": ["2.3", "4.6", "5.2", "6.3", "6.4", "6.5", "6.6"] },
    { "id": 4, "tasks": ["2.4", "2.5", "2.6", "2.7", "2.8"] },
    { "id": 5, "tasks": ["7"] },
    { "id": 6, "tasks": ["8.1", "9.1", "9.2"] },
    { "id": 7, "tasks": ["8.2", "8.7", "9.3", "9.7", "9.8", "9.10"] },
    { "id": 8, "tasks": ["8.3", "8.4", "8.5", "8.6", "8.8", "8.9", "9.4", "9.5", "9.6", "9.9"] },
    { "id": 9, "tasks": ["10"] },
    { "id": 10, "tasks": ["11.1", "11.2", "11.3", "11.4", "11.5"] },
    { "id": 11, "tasks": ["12.1", "12.2", "12.3", "12.4", "12.5", "12.6", "13.1", "13.2", "13.3", "13.4", "13.5"] },
    { "id": 12, "tasks": ["13.6", "14.1", "14.2"] },
    { "id": 13, "tasks": ["14.3", "14.4", "14.5"] },
    { "id": 14, "tasks": ["15"] }
  ]
}
```
