# Implementation Plan: Agent Harness Platform

## Overview

Tasks follow the phases in `design.md` § Rollout. Each phase is shippable on its own and ends with a checkpoint. Within a task, write the named tests first, watch them fail, then implement.

Conventions for every task:

- Runtime code is Python 3.10+ standard library and POSIX `sh`. Dev-only tools are pinned in `requirements-dev.txt`.
- Every new test carries a Validates_Tag (`# Validates: agent-harness-platform/R<n>.<m>`).
- Every user-visible change updates the matching page in `docs/` and `docs/IMPLEMENTATION_STATUS.md` in the same task.
- A task is checked only when its tests pass in the Validation_Command (and the property suite, where named). Trust the Traceability_Report over checkboxes once Task 21 lands.

## Tasks

### Phase 0: Baseline

- [x] 1. Establish a clean baseline
  - [x] 1.1 Commit the current work
    - Review and commit the pending edits to the Template spec `tasks.md`, `tasks.meta.json`, and the new root `CLAUDE.md` on a branch, with a pull request
    - _Requirements: 1.1_
  - [x] 1.2 Reconcile the Template spec task list
    - For each task in `.kiro/specs/kiro-agent-harness-template/tasks.md`, find the code and tests it names, run them, and set the checkbox from the result
    - Add a reconciliation table (task, evidence, result) to `docs/IMPLEMENTATION_STATUS.md`
    - _Requirements: 1.2_
  - [x] 1.3 Clear the 16 `PLACEHOLDER-STALE` warnings
    - Already cleared before Phase 0 started (validator reported 0 warnings); this task added the regression test
    - Add a test in `tests/validator/test_template_content.py` that the shipped Template produces zero warnings
    - _Requirements: 1.3_
  - [x] 1.4 Close the Template spec known gaps
    - Write ADR 0001 to 0005 (or amend Template spec criteria 4.4, 8.9/10.8, 9.7, 10.1, 8.8) for the five gaps listed in the Template design, and add or update the tests that pin the chosen behavior
    - _Requirements: 1.4, 16.2_

- [x] 2. Add continuous integration and the traceability seed
  - [x] 2.1 Create `.github/workflows/ci.yml`
    - Matrix ubuntu and macos, Python 3.10 and newest 3.x; run `scripts/validate.sh` and `HYPOTHESIS_PROFILE=ci scripts/test-properties.sh`
    - `permissions: contents: read`; every action pinned by full SHA with a version comment
    - Add a validator test that parses the workflow and rejects unpinned actions or broader permissions without a justification comment
    - _Requirements: 2.1, 2.2, 2.3, 2.5_
  - [x] 2.2 Create `.github/workflows/integration.yml`
    - Manual and weekly triggers only; skip for fork pull requests; runs `HARNESS_INTEGRATION=1` suite; not a required check
    - _Requirements: 2.4_
  - [x] 2.3 Retro-tag existing tests
    - Add Validates_Tags to every test in `tests/hooks`, `tests/validator`, `tests/property`, using the Template tasks' "Validates" lines and design property mapping
    - Write a temporary script that lists Template criteria with no tag; record the list in `docs/IMPLEMENTATION_STATUS.md` as the coverage backlog for Task 21
    - _Requirements: 14.2_
  - [x] 2.4 Document CI
    - README status badge; Customization_Guide section "Enable, change, or remove CI" replacing the current sample-only text
    - _Requirements: 2.6_

- [x] 3. Checkpoint: Phase 0
  - Validation_Command and property suite pass locally and in CI; zero warnings; status doc updated; tag release 0.2.0
  - _Requirements: 1.1, 1.3, 2.1_

### Phase 1: Kiro verification

- [ ] 4. Capture real Kiro payloads
  - [x] 4.1 Write the probe hook
    - `.kiro/hooks/examples/payload-probe.json` (disabled) and `payload-probe.sh` writing masked stdin to `.harness/probe/<trigger>/<timestamp>.json` (git-ignored)
    - Unit tests: masking of every secret pattern, path normalization, never writes outside the probe directory
    - _Requirements: 3.1, 11.4_
  - [ ] 4.2 Record fixtures on each supported Kiro version
    - Enable the probe, trigger each event used by the enabled hooks, copy the masked payloads to `tests/fixtures/payloads/kiro/<version>/<trigger>/`
    - Add a validator test that every enabled Hook_File trigger has at least one fixture per recorded version
    - _Requirements: 3.2_
  - [x] 4.3 Fixture-driven hook tests
    - `tests/hooks/test_kiro_fixtures.py`: run each wrapper on each fixture and assert the Template spec outcome (block, ask, pass, message)
    - _Requirements: 3.3_

- [ ] 5. Manual Kiro IDE verification
  - [x] 5.1 Create the Manual_Check_Record format and the first records
    - Done: format, validator check, template, and `docs/verification/kiro/RUNBOOK.md`. The records themselves need a human in Kiro IDE (see the runbook), so Tasks 4.2, 5.2 values, 5.3, and the Phase 1 checkpoint wait for them
    - `docs/verification/README.md` with the front matter schema; one record per check in Requirement 3.4 per Kiro version
    - _Requirements: 3.4_
  - [ ] 5.2 Publish the verified version range
    - Update `tech.md` (via its future Guidance_Source), README, and a first `harness/capabilities.json` with the Kiro row only
    - _Requirements: 3.5_
  - [ ] 5.3 Handle contract gaps
    - For any failed check, record the gap, implement the documented fallback (for example deny instead of ask where ask is not honored), and add a test for the fallback
    - _Requirements: 3.6_

- [ ] 6. Checkpoint: Phase 1
  - All Requirement 3 checks recorded with verdicts; fixture tests pass; release 0.3.0
  - _Requirements: 3.4, 3.5_

### Phase 2: Agent-neutral core

- [x] 7. Verify other Agents' formats (research, no code)
  - For Claude Code, Cursor, GitHub Copilot, Codex, and Gemini CLI: read the official docs, install the current version, capture one payload per hook event with a probe, and fill the Capability_Matrix rows with dated sources
  - Write ADR "Supported Agents and protection levels" from the results; drop or defer any Agent whose hooks cannot be verified
  - _Requirements: 9.1_

- [x] 8. Build the event model and Kiro Adapter
  - [ ] 8.1 `harness/core/event.py`
    - Dataclasses, schema version, category and trigger enums; unit tests for validation of each field
    - _Requirements: 4.1_
  - [ ] 8.2 Adapter protocol and Kiro Adapter
    - Move `hookio.py` decoding into `adapters/kiro.py`; Tool_Map from `capabilities.json`; encode exit codes, stdout JSON, stderr text
    - Leave re-export shims in `.kiro/hooks/scripts/lib/`
    - _Requirements: 4.2, 4.3_
  - [ ] 8.3 Failure semantics and unknown tools
    - Decode errors, oversize input, and deadlines map to each guard's failure Decision; unmapped tools become `other`
    - _Requirements: 4.4, 4.5_
  - [ ] 8.4 Guard combination
    - One combined entry point per event; first deny, then first ask, then allow
    - _Requirements: 4.7_
  - [ ] 8.5 Property tests
    - **Property 29: Adapter round trip** (`test_p29_adapter_roundtrip.py`)
    - **Property 30: Decode failure applies guard failure semantics** (`test_p30_decode_failure.py`)
    - **Property 32: Guard combination order** (`test_p32_guard_combination.py`)
    - **Property 33: Unknown tools with command fields ask** (`test_p33_unknown_tools.py`)
    - _Requirements: 4.2, 4.4, 4.5, 4.6, 4.7_

- [x] 9. Move policy and guards into the core
  - [ ] 9.1 Policy_Files to `harness/policy/`
    - Move the lists, keep generated copies at the old paths for one minor release; extend `risky-tools.conf` with `category:` and `<agent>:` tool forms
    - _Requirements: 5.1, 5.2_
  - [ ] 9.2 Policy validation
    - `harness_validator/policy.py`: unknown category, unknown Agent, bad regex; unit tests per error
    - **Property 44: Policy_File parse round trip** (`test_p44_policy_roundtrip.py`)
    - _Requirements: 5.4_
  - [ ] 9.3 Guards as pure functions
    - Move destructive, risky, prompt secret guards to `harness/core/guards/`; existing Template tests must pass unchanged through the shims
    - Keep list-driven tests reading Policy_Files at run time, parameterized over every Adapter
    - _Requirements: 5.1, 5.5_
  - [ ] 9.4 Kiro equivalence checkpoint
    - Run the full Template unit, property, and fixture suites against the new core; switch wrappers to the core; remove nothing yet
    - _Requirements: 6.8_

- [x] 10. Checkpoint: Phase 2
  - Kiro behavior unchanged (all Template tests and Kiro fixtures pass); release 0.4.0
  - _Requirements: 4.1, 5.1_

### Phase 3: Generator and portable guidance

- [x] 11. Manifest and Generator core
  - [x] 11.1 Manifest and schema
    - `harness/manifest.json`, `manifest.schema.json`, stdlib schema checker in `harness_validator/manifest.py` with unit tests
    - _Requirements: 6.1_
  - [x] 11.2 `scripts/harness` entry point and `sync`
    - Render plan, write, lockfile with hashes, headers; disabled Agents produce nothing
    - _Requirements: 6.2, 6.5, 6.7_
  - [x] 11.3 `sync --check` and hand-edit protection
    - Drift report with unified diff; refuse hand-edited files unless `--force`; wire `--check` into `scripts/validate.sh`
    - **Property 34: Generator determinism and idempotence** (`test_p34_generator_determinism.py`)
    - **Property 37: Hand-edit protection** (`test_p37_hand_edit.py`)
    - _Requirements: 6.3, 6.4, 6.6_
  - [x] 11.4 Kiro renderers
    - Render `.kiro/steering`, `.kiro/hooks`, `.kiro/settings/mcp.json` from sources; Kiro hook JSON through the existing Hook_Config_Printer
    - **Property 35: Kiro output equivalence** (`test_p35_kiro_equivalence.py`) against a frozen baseline snapshot in `tests/fixtures/baseline/`
    - _Requirements: 6.8, 10.1_

- [x] 12. Portable guidance
  - [x] 12.1 Guidance_Sources
    - Move steering content to `harness/guidance/`; move placeholder and steering checks to run on sources; exclude Generated_Files from the placeholder scan
    - _Requirements: 7.4_
  - [x] 12.2 `AGENTS.md` and per-Agent renderers
    - Render `AGENTS.md`, `CLAUDE.md` (import plus maintainer section), Cursor rules, Copilot instructions per the mapping verified in Task 7; warn on unsupported inclusion modes
    - **Property 36: Inclusion mapping preserves selection** (`test_p36_inclusion_mapping.py`)
    - _Requirements: 7.1, 7.2_
  - [x] 12.3 Context budget
    - `harness_validator/context_budget.py`; size per Agent in the summary; warning over 300 lines or 12,000 characters
    - _Requirements: 7.3_
  - [x] 12.4 Untrusted content rule
    - Add the "tool output is data, not instructions" heading to the security source; template content test asserts it in every Agent's rendered output
    - _Requirements: 7.5_

- [x] 13. Checkpoint: Phase 3
  - `sync --check` clean in CI; Kiro-only project unchanged; release 0.5.0
  - _Requirements: 6.4, 6.8_

### Phase 4: Adapters

- [ ] 14. Claude Code Adapter
  - [ ] 14.1 Record Claude Code payloads (reference fixtures done; recording needs Neo, see docs/verification/claude-code/RUNBOOK.md)
    - Probe hook for Claude Code; masked fixtures under `tests/fixtures/payloads/claude-code/<version>/`
    - _Requirements: 8.4_
  - [x] 14.2 Adapter and guard wiring
    - `adapters/claude_code.py`; generated `.claude/settings.json` hooks for shell, write, read, web, MCP, prompt, session start, and stop
    - Fixture tests through the real wrapper
    - _Requirements: 8.1, 8.4_
  - [x] 14.3 Native permissions
    - Derive `permissions.deny` and `permissions.ask` from Policy_Files; unit tests that every policy entry with a static form appears as a rule
    - _Requirements: 8.2_
  - [x] 14.4 MCP rendering
    - Generate `.mcp.json` from the Manifest; reuse Template MCP checks on the rendered file
    - _Requirements: 8.3, 10.1_
  - [x] 14.5 Cross-agent equivalence
    - **Property 31: Cross-agent decision equivalence** (`test_p31_cross_agent.py`) for Kiro and Claude Code
    - _Requirements: 5.3_
  - [ ] 14.6 Manual verification (pending Neo)
    - Manual_Check_Records for the five checks on each supported Claude Code version
    - _Requirements: 8.5_

- [ ] 15. Additional Adapters (only Agents verified in Task 7)
  - [ ] 15.1 One Adapter per verified Agent with hooks (none: only Kiro and Claude Code were verifiable on 2026-11-21)
    - Same structure as Task 14: fixtures, Adapter, generated hook config, fixture tests, extend Property 31 to the new Agent
    - _Requirements: 9.2_
  - [x] 15.2 Degraded protection rendering
    - Permission-only and guidance-only rendering; protection level table in README generated from the Capability_Matrix
    - _Requirements: 9.3_
  - [x] 15.3 Capability checks
    - `harness_validator/capabilities.py`: missing entry is an error; verification older than 180 days is a warning
    - _Requirements: 9.4_
  - [x] 15.4 Per-Agent guide sections
    - Customization_Guide sections per Agent with protection levels, generated files, and verification steps; each with an `example=` block
    - _Requirements: 9.5_

- [ ] 16. MCP supply chain
  - [x] 16.1 Tool inventories (tooling and tests done; recording against the real pinned servers needs uvx and network)
    - `harness/mcp/<server>.tools.json` generated by an opt-in script from the pinned server; integration test compares live tools with the inventory
    - _Requirements: 10.2, 10.3_
  - [x] 16.2 Validator checks
    - `autoApprove` within inventory; minimum versions enforced for every rendered MCP file
    - _Requirements: 10.4, 10.6_
  - [x] 16.3 Advisory lookup
    - Extend `scripts/check-mcp-updates.sh` with an OSV query; test with a recorded OSV response fixture; still never edits files
    - _Requirements: 10.5_

- [ ] 17. Checkpoint: Phase 4
  - Claude Code "enforced" with fresh Manual_Check_Records; other Agents at their verified level; release 0.6.0
  - _Requirements: 8.5, 9.3_

### Phase 5: Security, observability, and quality gates

- [x] 18. Protected paths and egress
  - [x] 18.1 Protected-path guard
    - `harness/policy/protected-paths.txt` with defaults and `!` re-includes; guard for read, write, delete, and shell read commands; fail closed on a missing list
    - **Property 38: Protected-path decisions** (`test_p38_protected_paths.py`)
    - _Requirements: 11.1, 11.2, 11.5_
  - [x] 18.2 Egress allowlist
    - `egress-allowlist.txt`; risky guard asks for any `web` category call to an unlisted host, for every Adapter
    - _Requirements: 11.3_
  - [x] 18.3 Secret non-disclosure
    - **Property 39: No secret reaches any output channel** (`test_p39_no_secret_leak.py`) over stdout, stderr, Decision_Log, fixtures, and reports
    - _Requirements: 11.4_

- [x] 19. Decision_Log
  - [x] 19.1 Logger
    - Append-only JSON Lines, masking, truncation, rotation at 5 MB with 3 files, `HARNESS_DECISION_LOG=0` opt-out, `.gitignore` entry
    - _Requirements: 12.1, 12.2, 12.4_
  - [x] 19.2 Failure isolation
    - **Property 40: Decision_Log failures never change the Decision** (`test_p40_log_failure.py`)
    - _Requirements: 12.3_
  - [x] 19.3 `harness log --summary`
    - Counts per guard and top ten matched entries; unit tests over a fixture log
    - _Requirements: 12.5_

- [x] 20. Spec_Linter and spec scaffolding
  - [x] 20.1 Structure and EARS checks
    - `harness_validator/spec_lint.py` for every spec directory
    - **Property 43: EARS classification** (`test_p43_ears.py`)
    - _Requirements: 13.1, 13.2, 13.3_
  - [x] 20.2 Task reference checks
    - **Property 41: Spec_Linter task references** (`test_p41_task_refs.py`); run the linter on this spec and the Template spec and fix findings
    - _Requirements: 13.4_
  - [x] 20.3 `harness new-spec`
    - Skeleton that passes the linter; refuses an existing directory; Kiro `.config.kiro` included
    - _Requirements: 13.5_
  - [x] 20.4 Spec workflow guidance
    - Manual Guidance_Source "spec-workflow" rendered for Agents without a spec mode
    - _Requirements: 13.6_

- [x] 21. Traceability and coverage gates
  - Runs after the Spec_Linter task because it reuses its requirement and task parsers
  - [x] 21.1 `harness trace`
    - Parse criteria, task references, Validates_Tags, Manual_Check_Records, last test results; print Markdown and write `build/traceability.json`; list skipped tests with reasons
    - **Property 42: Traceability completeness** (`test_p42_traceability.py`)
    - _Requirements: 14.1, 14.6_
  - [x] 21.2 Trace check in the validator
    - Uncovered criteria and dangling tags are errors for this spec and the Template spec; close the backlog from Task 2.3
    - _Requirements: 14.2_
  - [x] 21.3 Coverage gate
    - Pin a coverage tool in `requirements-dev.txt`; CI fails under 90 percent line or 80 percent branch per package
    - _Requirements: 14.3_
  - [x] 21.4 Mutation testing
    - Pin a mutation tool; `nightly.yml` runs it on guard modules; fail under 85 percent with surviving mutants listed; add tests until the threshold holds
    - _Requirements: 14.4_
  - [x] 21.5 Property test conventions
    - Validator test that each of Properties 29 to 44 has exactly one module with the matching number and tag
    - _Requirements: 14.5_

- [x] 22. Evals
  - [x] 22.1 Scenario runner
    - `evals/scenarios/*.json` (at least 20), runner that renders native payloads per Adapter and runs the real wrappers; wired into `scripts/validate.sh`
    - _Requirements: 15.1_
  - [x] 22.2 Bypass_Corpus
    - At least 50 labeled items; runner fails on an allowed `must-block`; report `known-gap` counts; improve the destructive patterns where cheap and safe
    - _Requirements: 15.2, 15.3_
  - [x] 22.3 Limits documentation
    - Customization_Guide section on known gaps and sandbox recommendation; README shows corpus results
    - _Requirements: 15.4_
  - [x] 22.4 Live evals
    - Opt-in drivers per Agent CLI in a temporary Template copy; results saved as Manual_Check_Records; excluded from PR CI
    - _Requirements: 15.5_

- [ ] 23. Checkpoint: Phase 5
  - Trace check clean, coverage and mutation gates green, Bypass_Corpus has zero allowed `must-block`; release 0.9.0
  - _Requirements: 14.2, 14.3, 15.3_

### Phase 6: Documentation and release

- [ ] 24. Documentation restructure
  - [ ] 24.1 Diataxis layout
    - Split README, CUSTOMIZING, PROJECT_OVERVIEW, GIT_HOOKS into tutorials, how-to, reference, and explanation; `docs/README.md` index; redirects or stubs for old paths
    - _Requirements: 16.1_
  - [ ] 24.2 ADRs for every design decision
    - ADRs for D1 to D8 and the Task 7 Agent decision, each listing affected Criterion_IDs
    - _Requirements: 16.2_
  - [ ] 24.3 Reference pages and help parity
    - `docs/reference/cli.md` and Policy_File format pages; test that each command's `--help` options match its page
    - _Requirements: 16.3_
  - [ ] 24.4 Executable examples and link check
    - Extend `test_docs_examples.py` to the `example=<target>` forms for guards and the Generator; `docs_links.py` for relative links
    - _Requirements: 16.4, 16.6_
  - [ ] 24.5 CHANGELOG
    - `CHANGELOG.md` with entries back to 0.1.0; validator check that `harness/VERSION` has an entry
    - _Requirements: 16.5_

- [ ] 25. Install, upgrade, doctor
  - [ ] 25.1 Versioning policy
    - `harness/VERSION`; ADR on what counts as a major change
    - _Requirements: 17.1_
  - [ ] 25.2 `harness init`
    - Copy, write Manifest with selected Agents, sync, validate; refuse to overwrite without `--force`; tests in a temporary directory with and without an existing git repo
    - _Requirements: 17.2_
  - [ ] 25.3 `harness upgrade`
    - Three-way merge using the lockfile hashes as the base; conflicts reported, files left unchanged; tests with edited and unedited files
    - _Requirements: 17.3_
  - [ ] 25.4 `harness doctor`
    - Runtime, Agents, protection levels, drift, log status; non-zero exit on missing required runtime; tests with `PATH` stripped
    - _Requirements: 17.4_
  - [ ] 25.5 Release checklist
    - Update the release-checklist Guidance_Source with the gates in Requirement 17.5; validator test that the checklist names each gate
    - _Requirements: 17.5_

- [ ] 26. Final checkpoint: 1.0.0
  - CI green on the full matrix, trace check zero errors, Manual_Check_Records fresh for every "enforced" Agent, CHANGELOG entry, tag 1.0.0
  - _Requirements: 14.2, 17.5_
