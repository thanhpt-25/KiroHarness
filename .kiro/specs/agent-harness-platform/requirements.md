# Requirements Document

## Introduction

This spec plans the next stage of KiroHarness: from a verified Kiro IDE template to a best-practice agent harness that keeps Kiro as the first-class target and also serves other AI coding agents (Claude Code, Cursor, GitHub Copilot, OpenAI Codex, Gemini CLI) from one source of truth.

It builds on the shipped implementation described in `.kiro/specs/kiro-agent-harness-template/` (the "Template spec"): steering files, seven v1 hooks, fail-closed and fail-to-ask guards, a pinned MCP configuration, the offline Config_Validator, 95 unit tests and 28 property tests. Every requirement in the Template spec stays in force unless a criterion below says it is replaced.

Three principles apply to every requirement:

1. **Spec-driven.** No behavior lands without an acceptance criterion in a spec, a design entry that explains it, and a task that implements it.
2. **Documented.** Every user-visible behavior, command, file format, and decision is documented, and documentation examples are executed by tests.
3. **Tested.** Every acceptance criterion is linked to at least one automated test or, where automation is impossible, to a recorded manual check with a date and environment.

Requirements are grouped by delivery phase (0 to 6). The phase order is the recommended build order; see `design.md` § Rollout.

## Glossary

Terms already defined in the Template spec glossary (Template, Steering_File, Hook_File, Hook_Definition, Hook_Trigger, Destructive_Command_Guard, Destructive_Command_List, Risky_Tool_Guard, Risky_Tool_List, Quality_Hook, MCP_Config, MCP_Server_Entry, Secret_Reference, Placeholder, Env_Example_File, Config_Validator, Validation_Report, Validation_Command, Template_README, Customization_Guide) keep their meaning here.

- **Harness**: The Template plus everything this spec adds: the agent-neutral core, the adapters, the generator, and the quality tooling.
- **Agent**: An AI coding tool that the Harness configures. The supported set is listed in the Capability_Matrix.
- **Primary_Agent**: Kiro IDE. The Harness treats it as the reference Agent; every safety behavior is available for it.
- **Adapter**: The code and templates that translate between one Agent's native formats (hook payloads, hook outputs, config files, instruction files) and the Harness core.
- **Capability_Matrix**: The machine-readable file `harness/capabilities.json` that records, for each Agent and Agent version range, which Harness features the Agent supports natively, which are emulated, and which are unavailable, with the date and source of verification.
- **Harness_Event**: The agent-neutral, normalized representation of a hook invocation, defined in `design.md` § Data Models.
- **Decision**: The result of evaluating a Harness_Event against policy. One of `allow`, `ask`, or `deny`, with a reason string.
- **Policy_File**: An agent-neutral data file in `harness/policy/` that drives a guard, for example the Destructive_Command_List or the Risky_Tool_List.
- **Tool_Category**: An agent-neutral class of tool: `shell`, `read`, `write`, `delete`, `web`, `mcp`, `spec`, or `other`.
- **Tool_Map**: The per-Agent table in the Capability_Matrix that maps each native tool ID to a Tool_Category and to the payload fields that hold its command, path, or URL.
- **Manifest**: The canonical file `harness/manifest.json` that lists the guidance documents, guards, quality checks, and MCP servers the Harness provides, independent of any Agent.
- **Generator**: The command `scripts/harness sync` that renders every Agent's native files from the Manifest, the Policy_Files, and the guidance sources.
- **Generated_File**: A file written by the Generator. It starts with a generated-file header that names its sources and the Harness version.
- **Drift**: A difference between a Generated_File on disk and the output the Generator would write for the current sources.
- **Guidance_Source**: A Markdown file under `harness/guidance/` with front matter that the Generator renders into each Agent's instruction format (Kiro steering, `AGENTS.md`, `CLAUDE.md`, Cursor rules, Copilot instructions).
- **Always_On_Context**: The guidance an Agent loads into every session regardless of which files are open.
- **Spec_Linter**: The Config_Validator checks that apply to every spec directory in `.kiro/specs/`.
- **Criterion_ID**: The identifier `R<n>.<m>` of acceptance criterion `m` of requirement `n` in a spec, qualified by the spec directory name when ambiguous (for example `agent-harness-platform/R4.2`).
- **Validates_Tag**: A comment in a test module, in the form `Validates: <spec>/R<n>.<m>[, ...]`, that links the test to one or more Criterion_IDs.
- **Manual_Check_Record**: An entry in `docs/verification/` that records a manual verification: Criterion_IDs, date, Agent and version, operating system, steps, observed result, and verdict.
- **Traceability_Report**: The output of `scripts/harness trace`, which maps every Criterion_ID to its tasks, tests, and Manual_Check_Records.
- **Decision_Log**: The local, git-ignored JSON Lines file `.harness/logs/decisions.jsonl` where guards record each Decision.
- **Eval_Scenario**: A scripted, deterministic sequence of Harness_Events with expected Decisions, stored under `evals/scenarios/`.
- **Bypass_Corpus**: The list of known command obfuscations, stored under `evals/corpus/`, used to measure how well the Destructive_Command_Guard resists evasion.
- **Harness_Version**: The semantic version of the Harness, stored in `harness/VERSION`.
- **ADR**: An architecture decision record in `docs/adr/NNNN-<slug>.md`.

## Requirements

### Phase 0: Baseline

### Requirement 1: Baseline Hygiene

**User Story:** As the Harness maintainer, I want the current implementation committed, reconciled, and warning-free, so that new work starts from a known-good baseline.

#### Acceptance Criteria

1. THE Harness SHALL have every file of the current implementation committed to version control, with no uncommitted changes in tracked files, before the first task of Phase 1 starts.
2. THE Template spec `tasks.md` SHALL mark each task as complete if and only if the code and the tests named in that task exist and pass, as shown by the Traceability_Report or, before that report exists, by a reconciliation table in `docs/IMPLEMENTATION_STATUS.md`.
3. WHEN the Validation_Command runs on the baseline, THE Config_Validator SHALL report zero errors and zero `PLACEHOLDER-STALE` warnings.
4. THE Template spec SHALL record each of the five entries of its design section "Known Gaps Requiring Requirements Changes" as either an amended acceptance criterion in its `requirements.md` or an ADR that accepts the deviation.

### Requirement 2: Continuous Integration

**User Story:** As the Harness maintainer, I want every push and pull request checked automatically, so that local, bypassable Git hooks are not the only gate.

#### Acceptance Criteria

1. THE Harness SHALL provide a CI workflow in `.github/workflows/` that runs the Validation_Command and the property suite on every push and every pull request, on Linux and macOS, with Python 3.10 and the newest stable Python 3 release.
2. THE CI workflow SHALL set the workflow token permissions to `contents: read` unless a job documents in a comment why it needs more, and SHALL reference every third-party action by a full commit SHA with the version in a trailing comment.
3. THE CI workflow SHALL run the property suite with `HYPOTHESIS_PROFILE=ci`.
4. THE CI workflow SHALL run the networked MCP integration suite only on a manual trigger or a weekly schedule, never on pull requests from forks, and SHALL not fail the push or pull request checks because of it.
5. IF any CI job fails, THEN THE CI workflow SHALL report the failing test names and Config_Validator errors in the job log in the same `detail(input, expected, actual)` format the Validation_Command prints.
6. THE Template_README SHALL show the CI status and THE Customization_Guide SHALL explain how an adopting project enables, changes, or removes the workflow.

### Phase 1: Kiro verification

### Requirement 3: Kiro IDE Contract Verification

**User Story:** As a developer using Kiro, I want the hooks verified against real Kiro IDE builds, so that the guards I rely on actually block and ask in my IDE.

#### Acceptance Criteria

1. THE Harness SHALL provide a disabled probe Hook_File in `.kiro/hooks/examples/` that writes the raw stdin payload of each Hook_Trigger it is enabled for to a git-ignored directory, with Secret_Pattern masking applied before writing.
2. THE Harness SHALL store recorded Kiro payloads, after masking and with absolute user paths replaced by a fixed root, under `tests/fixtures/payloads/kiro/<kiro-version>/<trigger>/`, with at least one payload for each Hook_Trigger used by an enabled Hook_File in the Template.
3. THE Harness SHALL provide tests that run each enabled Hook_Script against every recorded payload for its trigger and assert the outcome defined for it in the Template spec.
4. THE Harness SHALL record one Manual_Check_Record per supported Kiro version for each of these checks: the Destructive_Command_Guard blocks `git push --force` and the agent receives the reason; the Risky_Tool_Guard causes Kiro to prompt for approval; the Quality_Hook receives the saved path; the prompt secret scan blocks a prompt with a test secret; the git MCP server operates only on the workspace repository.
5. THE `tech.md` Steering_File and the Template_README SHALL state the minimum and maximum verified Kiro IDE versions, and THE Capability_Matrix SHALL record the same range with the verification date.
6. IF a Manual_Check_Record shows that a Kiro version does not honor a guard contract (for example `permissionDecision` `"ask"`), THEN THE Harness SHALL record the gap in the Capability_Matrix and in `docs/IMPLEMENTATION_STATUS.md`, and THE affected guard SHALL fall back to the strongest behavior that version honors, documented in the Customization_Guide.

### Phase 2: Agent-neutral core

### Requirement 4: Normalized Event Model

**User Story:** As the Harness maintainer, I want one internal event format for all Agents, so that guard logic is written and tested once.

#### Acceptance Criteria

1. THE Harness SHALL define the Harness_Event as a versioned data structure with the fields listed in `design.md` § Data Models, and every guard SHALL take a Harness_Event as its only input and return a Decision.
2. WHEN an Adapter receives a native hook payload, THE Adapter SHALL convert it to a Harness_Event using the Agent's Tool_Map, so that the guard sees the Tool_Category, the native tool ID, and the extracted command, paths, URL, or prompt.
3. WHEN a guard returns a Decision, THE Adapter SHALL encode it in the Agent's native output format (exit code, standard output JSON, standard error text) as recorded in the Capability_Matrix.
4. IF an Adapter cannot decode a payload, THEN THE Adapter SHALL produce the failure Decision defined for that guard (`deny` for the Destructive_Command_Guard and the secret guards, `ask` for the Risky_Tool_Guard), matching the failure semantics of Template spec Requirements 4.4 and 5.6.
5. IF a native tool ID is not in the Agent's Tool_Map, THEN THE Adapter SHALL classify it as Tool_Category `other` and THE Risky_Tool_Guard SHALL return `ask` for it when the payload contains a field that the Tool_Map lists as a command field for any Agent.
6. THE Harness_Event decoder and encoder for each Agent SHALL satisfy the round-trip property defined in `design.md` § Correctness Properties.
7. WHEN more than one guard applies to the same Harness_Event, THE Harness SHALL combine their Decisions so that the first `deny` wins, otherwise the first `ask` wins, otherwise the result is `allow`, and the combined reason SHALL name the deciding guard.

### Requirement 5: Portable Policy

**User Story:** As a developer, I want to edit one deny list and one ask list for every Agent I use, so that my safety policy does not diverge between tools.

#### Acceptance Criteria

1. THE Harness SHALL store the Destructive_Command_List, the Risky_Tool_List, the protected-path list from Requirement 11, and the egress allowlist as Policy_Files in `harness/policy/`, and every Adapter SHALL read these same files at run time.
2. THE Risky_Tool_List SHALL accept a Tool_Category (for example `category:delete`) or an Agent-qualified tool ID (for example `kiro:@git/git_reset`) in its tool column, in addition to the existing exact Kiro tool IDs, which SHALL keep their current meaning.
3. WHEN the same Harness_Event content is presented through two different Adapters, THE guards SHALL return the same Decision, except where the Capability_Matrix records that an Agent cannot express that Decision, in which case the Adapter SHALL apply the documented fallback.
4. THE Config_Validator SHALL report an error for a Policy_File entry that names an unknown Tool_Category, an Agent not in the Capability_Matrix, or a regular expression that does not compile.
5. THE Template spec Requirement 11.1 and 11.3 tests SHALL keep reading the Policy_Files at run time, so that a new policy entry is tested for every Agent that has an Adapter without any change to test code.

### Phase 3: Generator and portable guidance

### Requirement 6: Canonical Manifest and Generator

**User Story:** As a developer, I want to change guidance, guards, or MCP servers in one place and regenerate every Agent's files, so that I never hand-edit five copies of the same rule.

#### Acceptance Criteria

1. THE Harness SHALL provide the Manifest, with a JSON schema in `harness/manifest.schema.json`, that lists the enabled Agents, the Guidance_Sources, the guards with their triggers, the quality checks, and the MCP servers.
2. WHEN a developer runs `scripts/harness sync`, THE Generator SHALL write every Generated_File for every Agent enabled in the Manifest and SHALL write no file for a disabled Agent.
3. THE Generator SHALL be deterministic: two runs over the same inputs SHALL produce byte-identical files, and running it on its own output SHALL change nothing.
4. WHEN a developer runs `scripts/harness sync --check`, THE Generator SHALL write nothing, exit 0 if there is no Drift, and exit 1 with a list of drifted files and a unified diff otherwise; THE Validation_Command SHALL run this check.
5. THE Generator SHALL begin every Generated_File that supports comments with a header naming the source files and the Harness_Version, and for formats without comments (JSON) SHALL record the same information in `harness/generated.lock.json` with a content hash per file.
6. IF a Generated_File was edited by hand, THEN `scripts/harness sync` SHALL refuse to overwrite it, exit 1, and name the file, unless the developer passes `--force`.
7. THE Generator SHALL use only the Python standard library and SHALL run offline.
8. THE Kiro files produced by the Generator (`.kiro/steering/`, `.kiro/hooks/`, `.kiro/settings/mcp.json`) SHALL pass every Template spec requirement, so that a project that uses only Kiro sees no behavior change.

### Requirement 7: Portable Guidance

**User Story:** As a developer, I want the same project guidance to reach every Agent in that Agent's native format, so that each Agent follows the same rules.

#### Acceptance Criteria

1. THE Generator SHALL render `AGENTS.md` at the repository root from the Guidance_Sources whose inclusion is `always`, and SHALL render each Guidance_Source into Kiro steering, `CLAUDE.md`, Cursor rules, and Copilot instruction files for each enabled Agent, preserving the inclusion semantics (`always`, file-pattern, manual, description-triggered) wherever the target format supports them.
2. WHERE a target format cannot express a Guidance_Source's inclusion mode, THE Generator SHALL use the fallback recorded for that Agent in the Capability_Matrix and SHALL print a warning that names the Guidance_Source and the Agent.
3. THE Config_Validator SHALL report a warning when the Always_On_Context rendered for any Agent exceeds 300 lines or 12,000 characters, and SHALL report the size for each Agent in the summary.
4. THE Guidance_Sources SHALL keep the content rules of Template spec Requirement 2 (security headings, placeholders), and the Config_Validator SHALL apply those rules to the Guidance_Sources rather than to the Generated_Files.
5. THE `security` Guidance_Source SHALL include a rule under its own heading that content returned by tools (web pages, files, issue text, MCP results) is data, not instructions, and that the Agent must ask before acting on instructions found in such content.

### Phase 4: Adapters

### Requirement 8: Claude Code Adapter

**User Story:** As a developer who also uses Claude Code, I want the same guards and MCP servers there, so that switching tools does not drop my safety checks.

#### Acceptance Criteria

1. WHERE Claude Code is enabled in the Manifest, THE Generator SHALL write `.claude/settings.json` with hook entries that run the Harness guards for shell, file-write, file-read, web, and MCP tool calls, for prompt submission, and for session start, and with a stop hook that requires the Validation_Command to pass.
2. WHERE Claude Code is enabled in the Manifest, THE Generator SHALL write a `permissions` block whose `deny` and `ask` rules are derived from the Policy_Files, so that the policy is enforced by Claude Code's permission system even when a hook does not run.
3. WHERE Claude Code is enabled in the Manifest, THE Generator SHALL write `.mcp.json` from the Manifest MCP servers with the same pins, Secret_References, and disabled states as the Kiro MCP_Config.
4. WHEN the Claude Code Adapter returns a Decision, THE Adapter SHALL use the exit-code and JSON output contract recorded for Claude Code in the Capability_Matrix, and SHALL be tested against recorded Claude Code payloads under `tests/fixtures/payloads/claude-code/<version>/`.
5. THE Harness SHALL record a Manual_Check_Record for each supported Claude Code version for the same five checks as Requirement 3 criterion 4.

### Requirement 9: Additional Adapters and Capability Matrix

**User Story:** As a developer using Cursor, Copilot, Codex, or Gemini CLI, I want to know exactly which protections I get, so that I do not assume a guard is active when my tool cannot run it.

#### Acceptance Criteria

1. THE Capability_Matrix SHALL list, for each supported Agent, the guidance file formats, the hook events and their payload and output contracts, the permission mechanism, the MCP configuration file and schema, the verified version range, and the date and source of each entry.
2. WHERE an Agent supports hooks, THE Harness SHALL provide an Adapter for that Agent that meets Requirement 4 and is tested against recorded payloads for that Agent.
3. WHERE an Agent does not support a hook event that a guard needs, THE Generator SHALL render the guard's rule as guidance and as native permission rules where the Agent has them, and THE Template_README SHALL show the Agent's protection level as "enforced", "permission-only", or "guidance-only" for each guard.
4. THE Config_Validator SHALL report an error when the Manifest enables an Agent that has no Capability_Matrix entry, and a warning when an enabled Agent's verified version range is older than 180 days.
5. THE Customization_Guide SHALL contain one section per supported Agent that states its protection level per guard, the files the Generator writes for it, and the steps to verify it.

### Requirement 10: MCP Supply Chain

**User Story:** As a developer, I want MCP servers pinned, minimal, and checked for silent changes, so that a compromised or changed server cannot widen what the agent can do.

#### Acceptance Criteria

1. THE Manifest SHALL be the only place where MCP servers are declared, and THE Generator SHALL render each enabled Agent's MCP configuration from it, keeping Template spec Requirement 8 in force for every rendered file.
2. THE Harness SHALL store, for each MCP server, a tool inventory file in `harness/mcp/<server>.tools.json` that lists the server's tool names and a SHA-256 hash of each tool's name, description, and input schema for the pinned version.
3. WHEN the MCP integration suite runs, THE suite SHALL compare each server's live tool list with its tool inventory and fail, naming the server and tool, if a tool was added, removed, or changed.
4. THE Config_Validator SHALL report an error when an `autoApprove` entry names a tool that is not in that server's tool inventory.
5. WHEN a developer runs `scripts/check-mcp-updates.sh`, THE script SHALL also report known security advisories for each pinned package from the OSV database, and SHALL still never edit files.
6. THE Config_Validator SHALL report an error when a pinned MCP package version is below its minimum version in `scripts/validator-config.json`, for every Agent's rendered MCP configuration.

### Phase 5: Security, observability, and quality gates

### Requirement 11: Security Baseline Across Agents

**User Story:** As a developer, I want secrets and sensitive files protected regardless of which Agent I use, so that an agent cannot read or leak credentials.

#### Acceptance Criteria

1. THE Harness SHALL provide a protected-path guard that returns `deny` for read, write, and delete tool calls whose target path matches the protected-path Policy_File, which by default lists `.env`, `.env.*` except `.env.example`, `*.pem`, `*.key`, `id_rsa*`, `.ssh/`, `.aws/credentials`, and `.kiro/settings/mcp.local.json`.
2. WHEN a shell command reads a protected path with a common read command (`cat`, `less`, `head`, `tail`, `cp`, `base64`, `xxd`, `source`), THE protected-path guard SHALL return `deny` and name the path.
3. THE Risky_Tool_Guard SHALL return `ask` for every `web` Tool_Category call whose host is not on the egress allowlist Policy_File, for every Agent with an Adapter.
4. THE Harness SHALL never write a matched secret value to standard output, standard error, the Decision_Log, a recorded payload fixture, or a Validation_Report; only the masked form defined in Template spec Requirement 10.6 SHALL appear.
5. IF the protected-path Policy_File is missing, unreadable, or empty, THEN THE protected-path guard SHALL return `deny` with a message naming the file.

### Requirement 12: Decision Audit Log

**User Story:** As a developer, I want a local record of what the guards decided, so that I can review what the agent tried and tune the policy.

#### Acceptance Criteria

1. WHEN a guard returns a Decision, THE guard SHALL append one JSON object to the Decision_Log with the timestamp in UTC, the Agent, the Harness_Event trigger, the Tool_Category, the native tool ID, the Decision, the matched policy entry, and a masked, length-limited summary of the command, path, or URL.
2. THE Decision_Log SHALL be git-ignored, and THE Harness SHALL rotate it when it exceeds 5 MB, keeping at most 3 rotated files.
3. IF the Decision_Log cannot be written, THEN THE guard SHALL still return its Decision unchanged and write one warning to standard error.
4. WHERE the environment variable `HARNESS_DECISION_LOG=0` is set, THE guards SHALL not write the Decision_Log.
5. WHEN a developer runs `scripts/harness log --summary`, THE command SHALL print the count of each Decision per guard and the ten most frequent matched policy entries.

### Requirement 13: Spec-Driven Workflow Enforcement

**User Story:** As a developer, I want every spec checked for structure and traceability, so that requirements, design, and tasks stay aligned as the project grows.

#### Acceptance Criteria

1. THE Spec_Linter SHALL check every directory in `.kiro/specs/` that contains a `requirements.md`, and SHALL report an error for each missing file among `requirements.md`, `design.md`, and `tasks.md`.
2. THE Spec_Linter SHALL report an error when a `requirements.md` lacks an Introduction or Glossary section, when a requirement lacks a user story in the form "As a ..., I want ..., so that ...", or when an acceptance criterion does not start with one of the EARS keyword patterns (`THE`, `WHEN`, `WHILE`, `IF`, `WHERE`, or a combination of them).
3. THE Spec_Linter SHALL report an error when a `design.md` lacks any of the sections Overview, Architecture, Components and Interfaces, Data Models, Error Handling, and Testing Strategy.
4. THE Spec_Linter SHALL report an error when a task in `tasks.md` references a Criterion_ID that does not exist, and a warning for each Criterion_ID that no task references.
5. WHEN a developer runs `scripts/harness new-spec <name>`, THE command SHALL create `.kiro/specs/<name>/` with `requirements.md`, `design.md`, `tasks.md`, and a Kiro `.config.kiro` file, each filled with a skeleton that passes the Spec_Linter, and SHALL refuse to overwrite an existing directory.
6. THE `harness/guidance/` sources SHALL include a manual Guidance_Source that describes the spec workflow (requirements, then design, then tasks, then implementation with tests) for Agents that have no built-in spec mode.

### Requirement 14: Test Traceability and Quality Gates

**User Story:** As the Harness maintainer, I want proof that every requirement is tested and that the tests can catch real bugs, so that "well tested" is measured, not assumed.

#### Acceptance Criteria

1. WHEN a developer runs `scripts/harness trace`, THE command SHALL print the Traceability_Report for every spec and write it as JSON to `build/traceability.json`, listing for each Criterion_ID the tasks, the tests with a matching Validates_Tag, and the Manual_Check_Records.
2. THE Config_Validator SHALL report an error for each Criterion_ID in this spec and in the Template spec that has neither a test with a matching Validates_Tag nor a Manual_Check_Record, and an error for each Validates_Tag that names a Criterion_ID that does not exist.
3. THE CI workflow SHALL measure line and branch coverage of `scripts/harness_validator/`, `harness/core/`, and the hook library with a pinned, dev-only coverage tool, and SHALL fail when line coverage is below 90 percent or branch coverage is below 80 percent for any of these packages.
4. THE CI workflow SHALL run mutation testing on the guard modules on a weekly schedule with a pinned, dev-only tool, and SHALL fail when the mutation score of any guard module is below 85 percent, listing the surviving mutants.
5. THE Harness SHALL implement each correctness property in this spec's `design.md` as exactly one property test that carries the property number in its file name and a Validates_Tag.
6. IF a test is skipped in CI, THEN THE test SHALL state the reason in its skip message, and THE Traceability_Report SHALL list the skipped test and the Criterion_IDs it would have validated.

### Requirement 15: Agent Behavior Evals

**User Story:** As the Harness maintainer, I want end-to-end scenarios and a bypass corpus, so that I know how the Harness behaves against realistic agent action sequences, including adversarial ones.

#### Acceptance Criteria

1. THE Harness SHALL provide at least 20 Eval_Scenarios covering destructive commands, risky tools, protected paths, secret prompts, egress, and spec-task completion, and THE Validation_Command SHALL replay every Eval_Scenario through every Adapter offline and compare each Decision with the expected one.
2. THE Bypass_Corpus SHALL contain at least 50 obfuscated forms of Destructive_Command_List entries (for example flag reordering, quoting, variable expansion, `eval`, command substitution, and encoded pipelines), each labeled `must-block` or `known-gap`.
3. WHEN the eval runner processes the Bypass_Corpus, THE runner SHALL fail if any `must-block` item is allowed, and SHALL report the count of `known-gap` items that are still allowed.
4. THE Customization_Guide SHALL list every `known-gap` category and state that the Destructive_Command_Guard is a pattern-based safety net, not a sandbox, and SHALL recommend OS-level isolation for untrusted workloads.
5. WHERE `HARNESS_LIVE_EVALS=1` is set and an Agent's command-line interface is installed, THE eval runner SHALL run the live Eval_Scenarios for that Agent in a temporary copy of the Template and record the results as Manual_Check_Records; live evals SHALL never run in pull request CI.

### Phase 6: Documentation and release

### Requirement 16: Documentation Standards

**User Story:** As a developer adopting the Harness, I want documentation organized by what I am trying to do and kept true by tests, so that I can trust it.

#### Acceptance Criteria

1. THE Harness documentation SHALL be organized into tutorial, how-to, reference, and explanation sections under `docs/`, with an index in `docs/README.md` that links every document.
2. THE Harness SHALL record every decision in a `design.md` decision table as an ADR with status, context, decision, consequences, and the Criterion_IDs it affects.
3. THE Harness SHALL provide a reference page for every command in `scripts/` and every Policy_File format, and a test SHALL check that every command's `--help` output and its reference page list the same options.
4. WHEN a fenced example in `docs/` is tagged `example=<target>`, THE documentation tests SHALL copy it to the target location in a temporary Harness copy and run the Config_Validator, the Generator check, or the named guard on it, expecting the result stated in the tag.
5. THE Harness SHALL keep a `CHANGELOG.md` in Keep a Changelog format, and THE Config_Validator SHALL report an error when `harness/VERSION` has no matching CHANGELOG entry.
6. THE Config_Validator SHALL report an error for a relative Markdown link in `docs/`, the Template_README, or a spec that points to a file that does not exist.

### Requirement 17: Release, Installation, and Upgrade

**User Story:** As a developer, I want to install the Harness into my repository and upgrade it later without losing my customizations, so that adopting it is a one-time decision, not a fork.

#### Acceptance Criteria

1. THE Harness SHALL use semantic versioning in `harness/VERSION`, where a change to a guard's failure semantics, a Policy_File format, or the Harness_Event schema is a major version change.
2. WHEN a developer runs `scripts/harness init <target-dir>`, THE command SHALL copy the Harness into the target repository, write the Manifest with only the Agents the developer selects, run the Generator, and run the Validation_Command, and SHALL refuse to overwrite existing files unless `--force` is given.
3. WHEN a developer runs `scripts/harness upgrade --from <dir-or-tag>`, THE command SHALL update Harness-owned files, leave Policy_Files, Guidance_Sources, and the Manifest unchanged where the developer edited them, report each conflict with a three-way diff, and run the Validation_Command.
4. WHEN a developer runs `scripts/harness doctor`, THE command SHALL report the Harness_Version, the Python version, the presence of `git` and `uvx`, the enabled Agents and their protection levels, Drift, and the Decision_Log status, and SHALL exit non-zero if any required runtime is missing.
5. THE release process SHALL be documented as a checklist in the `release-checklist` Steering_File and SHALL require a passing CI run, a current Traceability_Report with zero errors, and Manual_Check_Records no older than 30 days for each Agent marked "enforced".
