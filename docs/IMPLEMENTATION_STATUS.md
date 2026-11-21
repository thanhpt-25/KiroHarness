# Implementation Status and Readiness

## Snapshot

This inventory reflects the workspace tree reviewed on 2026-11-21, after Phase 0 of the platform plan (`.kiro/specs/agent-harness-platform/`). Test results below were collected on that date.

## Implemented repository areas

| Area | Current implementation |
|---|---|
| Product and usage docs | Root README.md, docs/CUSTOMIZING.md, docs/PROJECT_OVERVIEW.md, docs/GIT_HOOKS.md, and this file. |
| Requirements and designs | .kiro/specs/kiro-agent-harness-template/ contains the detailed requirements, design, task plan, Kiro config, and task metadata. |
| Example spec | .kiro/specs/example-feature/ has requirements, design, and tasks documents. |
| Steering | .kiro/steering/ contains product, technology, structure, coding standards, security, testing, release checklist, and API design guidance. |
| Kiro hooks | .kiro/hooks/ contains active JSON definitions for destructive command guard, risky tool guard, quality on save, session start, prompt secret scan, post-task tests, and stop validation. The examples directory contains disabled file-create and pre-compact hooks. |
| Hook runtime | .kiro/hooks/scripts/ contains executable shell wrappers, Python modules now live in harness/core/ (agent-neutral core with event model, capability-driven adapters and a combined guard CLI, harness/bin/guard) and policy files in harness/policy/; quality-hook.conf stays beside the Kiro scripts. The modules include shared hook input parsing, destructive and risky guards, quality execution, subprocess deadlines, prompt scanning, session context, and post-task testing. |
| MCP setup | .kiro/settings/mcp.json configures pinned AWS documentation, fetch, and git servers. .env.example provides environment-variable documentation. |
| Config validator | scripts/harness_validator/ contains the CLI and modules for front matter, glob matching, hook parsing/rules, MCP config, placeholders, secrets, steering, environment examples, and reports. scripts/validate-config.sh is its shell entry point. |
| Validation and commands | scripts/validate.sh combines configuration validation with hook and validator unit tests. scripts/lint.sh and scripts/test.sh invoke project-configured commands from scripts/project-commands.env. scripts/check-mcp-updates.sh performs the separate opt-in network update check. |
| Git hooks | .githooks/pre-commit runs scripts/validate.sh; commit-msg enforces a non-blank subject of at most 72 characters with no trailing whitespace; pre-push runs the property suite offline using installed dependencies. scripts/install-git-hooks.sh opts this repository into .githooks through local core.hooksPath configuration. Installation is opt-in. |
| CI | .github/workflows/ci.yml runs scripts/validate.sh and the property suite (ci profile) on every push and pull request, on Ubuntu and macOS with Python 3.10 and the newest 3.x. .github/workflows/integration.yml runs the MCP integration suite on manual dispatch and weekly. Actions are SHA-pinned and the token is read-only; tests/validator/test_ci_workflows.py enforces both. |
| Decisions | docs/adr/ records the five Template design deviations (ADR 0001 to 0005). |
| Tests | tests/hooks/, tests/validator/, tests/integration/, and tests/property/ contain hook, validator, MCP integration, and Hypothesis property suites. tests/_result.py provides the aggregate test result runner. requirements-dev.txt pins Hypothesis; scripts/test-properties.sh runs the property suite. |

## Current test organization

- **Hook tests:** destructive guard behavior, risky guard decisions, and quality/lifecycle scripts. These use standard-library unittest and subprocesses.
- **Validator tests:** hook parsing and validation, steering glob/front matter behavior, secrets, template content, documentation examples, and the combined validation command.
- **Integration tests:** MCP server startup and tool/repository checks in tests/integration/test_mcp_servers.py. The customization guide documents the HARNESS_INTEGRATION=1 opt-in invocation because these tests start external servers and require network/dependencies.
- **Property tests:** 28 modules named test_p01 through test_p28 cover hook round-tripping and formatting, complete validation findings, parser/front matter behavior, guards, quality command handling, prompt scanning, MCP checks, report rendering, and placeholders.
- **Profiles:** tests/property/_profiles.py registers the default 100-example and ci 300-example Hypothesis profiles. scripts/test-properties.sh prefers uv and otherwise uses a local .venv.

- **Traceability:** every test module carries a `# Validates: <spec>/R<n>.<m>` tag. All 115 acceptance criteria of the Template spec are linked to at least one test module (checked with a one-off script during Phase 0; `scripts/harness trace` in platform Task 21 will automate it).

### Verification results (2026-11-21, Phase 0)

- scripts/validate.sh: passed. The validator reported 0 errors and 0 warnings. The unit suite ran 102 tests: 101 passed and 1 was skipped (the networked MCP suite).
- scripts/test-properties.sh: passed. The property suite ran 35 tests.
- The earlier 16 PLACEHOLDER-STALE warnings are gone; tests/validator/test_validator_main.py now asserts zero warnings on the checkout.
- CI has not run yet; the first run happens on the Phase 0 pull request.
- The MCP integration suite was not run; it is an opt-in networked check.

### Template task reconciliation (2026-11-21)

| Template task | Evidence | Result |
|---|---|---|
| 1 to 10 | Code in scripts/harness_validator/ and .kiro/hooks/scripts/; unit and property suites pass | Complete (already checked) |
| 11.3 MCP_Config and Env_Example_File | .kiro/settings/mcp.json and .env.example present; MCP content tests in tests/validator/test_template_content.py and Properties 20 to 24 pass | Complete (checkbox was stale, now checked) |
| 11.1, 11.2, 11.4, 11.5, 12 to 14 | Shipped content, validator entry point, guard and documentation tests pass | Complete (already checked) |
| 15 Final checkpoint | validate.sh and the property suite pass (results above) | Complete (now checked) |

## Remaining gaps and caveats

1. **Kiro IDE integration is environment-specific.** Hook payload fields, exit-code blocking, permissionDecision ask behavior, event ordering, and actual file paths need the manual integration checks in docs/CUSTOMIZING.md against a supported Kiro version.
2. **MCP integration is opt-in.** The checked-in integration suite is not part of the offline validation command; server downloads/startup require network access and the configured uvx runtime.
3. **CI is new.** The workflows are in place but have not completed a run yet; branch protection that requires the `ci` check is a repository setting to enable on GitHub.
4. **Task tracking is reconciled by hand.** The Template tasks.md matches the code as of the reconciliation table above. Until `scripts/harness trace` exists, keep checkboxes in sync manually.
5. **MCP versions and tool IDs need maintenance.** Pins are explicit, and the update script is opt-in. Review upstream releases, security advisories, Kiro tool identifiers, the risky-tool matcher, and validator policy together.
6. **Repository-root assumption for MCP git.** The configured git server uses --repository .; confirm Kiro starts the MCP process with the workspace root as its working directory, or follow the documented absolute-path alternative (ADR 0005).
7. **Python and shell prerequisites.** Hook wrappers and validator scripts require Python 3.10+ and POSIX sh. Their missing-runtime behavior is implemented in wrappers but remains part of platform verification.
8. **Git hook enforcement is local and bypassable.** The opt-in hooks improve developer feedback but do not replace CI or server-side branch protection. Pre-commit validates the working tree, including unstaged edits, so partial staging may produce findings outside the staged diff. Pre-push property tests take about 90 seconds in the recorded run and require Hypothesis to be installed locally.

## Operational commands

| Command | Purpose | Network |
|---|---|---|
| scripts/validate-config.sh | Run the config validator | No |
| scripts/validate.sh | Run the validator and hook/validator unit tests | No |
| scripts/test-properties.sh | Run Hypothesis property tests | May download Hypothesis through uv on first use |
| HARNESS_INTEGRATION=1 python3 -m unittest tests.integration.test_mcp_servers | Start and inspect configured MCP servers | Yes |
| scripts/check-mcp-updates.sh | Compare pinned MCP versions with current package versions | Yes |

## Readiness

The repository contains the core implementation. The local validator, unit suite, and property suite passed in the recorded run. A release-ready claim still requires Kiro IDE smoke tests on supported versions and the opt-in MCP integration check where applicable. Keep this status inventory synchronized with code changes and record the environment and date when those checks are performed.
