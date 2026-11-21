# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A reusable **Kiro IDE agent harness template**: steering Markdown, Kiro v1 hook definitions with their scripts, MCP server config, and an offline config validator, plus the tests for all of it. There is no application code here. The "product" is the `.kiro/` configuration and the Python/sh tooling that enforces and validates it.

The normative spec is `.kiro/specs/kiro-agent-harness-template/requirements.md` (with `design.md` for interfaces and data formats). `tasks.md` progress markers may lag behind the code, so trust code and tests over its checkboxes. `docs/IMPLEMENTATION_STATUS.md` records known gaps.

## Commands

Requires Python 3.10+ and POSIX `sh`. All commands run from the repo root.

```sh
scripts/harness sync [--check]       # regenerate Agent files from harness/manifest.json (drift is a validator error)
scripts/harness trace               # Traceability_Report; writes build/traceability.json
python3 -I evals/run.py [--corpus]  # replay eval scenarios / Bypass_Corpus through every Adapter
scripts/coverage.sh                 # coverage gate (needs requirements-dev.txt)
scripts/validate.sh                 # config validator + hook/validator unit tests (offline). Run before finishing.
scripts/validate-config.sh          # config validator only (exit 0 ok, 1 errors, 2 internal crash)
scripts/test-properties.sh          # Hypothesis property suite (uses uv, else creates .venv from requirements-dev.txt)
HARNESS_OFFLINE=1 scripts/test-properties.sh     # property suite with already-installed Hypothesis, no installs
HYPOTHESIS_PROFILE=ci scripts/test-properties.sh # 300 examples per test instead of 100

# Single unit test module / test (stdlib unittest, no pytest)
python3 -m unittest tests.hooks.test_destructive_guard
python3 -m unittest tests.validator.test_hookconfig.SomeTestCase.test_name

# Single property test (needs Hypothesis, e.g. from .venv)
.venv/bin/python -m unittest tests.property.test_p01_hook_roundtrip

# Opt-in, networked
HARNESS_INTEGRATION=1 python3 -m unittest tests.integration.test_mcp_servers
scripts/check-mcp-updates.sh        # compares MCP pins with PyPI; never edits files
scripts/install-git-hooks.sh        # sets local core.hooksPath=.githooks
```

`scripts/lint.sh <file>` and `scripts/test.sh [<file>]` are for the *host* project. They read `LINT_FILE_COMMAND` / `TEST_FILE_COMMAND` / `TEST_COMMAND` from `scripts/project-commands.env` (parsed as `KEY="value"` data, never sourced) and exit 3 with `not configured: <KEY>` while a value is empty or still a placeholder, which is the shipped state. They are not this repo's own test commands.

Optional Git hooks in `.githooks/`: pre-commit runs `scripts/validate.sh`; commit-msg requires a non-blank subject of 72 characters or fewer with no trailing whitespace; pre-push runs the property suite in offline mode.

## Architecture

```
Kiro IDE -> .kiro/hooks/<id>.json -> sh wrapper in .kiro/hooks/scripts/ -> python3 -I harness/core/<module>.py -> harness/policy/ and config text files
Any agent hook -> harness/bin/guard <agent> <trigger> -> adapters.py decode -> guards.py -> adapters.py encode (agent-neutral path)
scripts/validate.sh -> scripts/validate-config.sh -> python3 -I -m harness_validator (scripts/harness_validator/)
                    -> tests/_result.py runner over tests/hooks + tests/validator
```

**Hook runtime (`.kiro/hooks/scripts/`).** Each hook JSON (`version: "v1"`, `hooks` array) runs a thin POSIX sh wrapper that locates its own directory and `exec`s a Python module in `harness/core/` with `python3 -I` (isolated: no ambient `PYTHONPATH` or user site). `harness/core/hookio.py` parses the event JSON from stdin and accepts both Kiro 1.x snake_case (`tool_name`, `tool_input`) and Kiro 0.12 camelCase (`toolName`, `toolArgs`). The workspace root is derived from the file location, not from cwd. Policy lives in data files under `harness/policy/` so it can change without touching code: `destructive-commands.txt` (one deny regex per line), `risky-tools.conf` (`tool | reason | predicate` lines; the tool column is `category:<name>`, `<agent>:<tool-id>` or a legacy bare Kiro tool ID), plus `.kiro/hooks/scripts/quality-hook.conf`. Subprocesses run under deadlines with process-group kill (`harness/core/runner.py`).

**Agent-neutral core (`harness/`).** `harness/capabilities.json` is the machine-readable Capability_Matrix (events, tool maps, output contract per agent). `event_model.py` defines `HarnessEvent`/`Decision`/`combine` (first deny, else first ask, else allow); `adapters.py` decodes native payloads and encodes decisions per agent; `guards.py` holds pure guard functions and the registry; `guard_cli.py` is the entry point behind `harness/bin/guard`. Unmapped tools with a command-like field ask. Decode failure uses each guard's own failure semantics. Runtime modules are flat (no package) and put their own directory on `sys.path`, so import siblings by flat name only. Spec: `.kiro/specs/agent-harness-platform/`; ADR 0006 records the layout.

**Failure semantics are a deliberate contract:**
- Destructive command guard **fails closed**: a match, malformed input, missing policy, or missing python3 all exit 2 (block).
- Risky tool guard **fails to "ask"**: unusable input or policy requests user approval rather than allowing or blocking.
Preserve these when editing guards. Tests assert them.

**Generator (`scripts/harness`, `scripts/harness_cli/`).** `harness/manifest.json` (schema in `manifest.schema.json`, checked by `harness_validator/manifest.py`) plus `harness/guidance/*.md` and `harness/kiro/hooks/*.json` are the sources. `scripts/harness sync [--check] [--force]` renders `.kiro/steering`, `.kiro/hooks/<shipped>.json`, `.kiro/settings/mcp.json` (byte-identical to the frozen baseline in `tests/fixtures/baseline/`, except the Untrusted Tool Output section in security) and, for enabled Agents, `AGENTS.md`, `CLAUDE.md`, `.claude/rules`, `.cursor/rules`, `.github/copilot-instructions.md`. `plan.build_plan` is pure; `sync.py` writes, drift-checks and protects hand edits via `harness/generated.lock.json`. **Edit sources, never the generated files**; the validator reports DRIFT. Steering and placeholder checks run on `harness/guidance/`. ADR 0007.

**Claude Code and MCP.** `plan.render_claude_native` writes `.claude/settings.json` and `.mcp.json`; `permissions.py` derives deny/ask/allow rules from `harness/policy/` and the Manifest (rules without a static form are reported, not dropped). `mcp_inventory.py` records and checks `harness/mcp/<server>.tools.json` (opt-in, starts servers). `harness/capabilities.json` entries with `"hooks": false` (Cursor, Copilot) are guidance-only and have no Adapter. ADR 0008.

**Config validator (`scripts/harness_validator/`)** is standard-library-only and offline, with one module per concern: `hookconfig` (parse/print hook JSON, with round-trip and idempotence properties), `hook_rules`, `frontmatter` (a YAML subset parser), `steering`, `mcp`, `secrets`, `placeholders`, `envfile`, `globmatch`, `report`. `__main__.py` runs every checker, wrapping each in `Run.guarded` so one crashing checker becomes an `[INTERNAL]` finding instead of hiding the rest. It reuses guard parsing code by loading modules from `harness/core/` directly; it does not duplicate it. Tunables (secret regexes, MCP read-only allowlist, known mutating tools, minimum versions) are in `scripts/validator-config.json`.

**Tests.** `tests/_support.py` puts `scripts/` and `harness/core/` on `sys.path` and provides helpers (`run_script`, `tool_call`, `TemplateCopy` for a temp copy of the whole template). Failure messages use the `detail(input, expected, actual)` format that `validate.sh` prints. Property tests are `tests/property/test_pNN_*.py` (one per numbered design property) and must import `tests.property._profiles` first. `tests/validator/test_template_content.py` and `test_docs_examples.py` assert on shipped content and docs, so editing steering, hooks, or docs can break them.

## Conventions and gotchas

- **Runtime code stays stdlib-only.** Hypothesis (pinned in `requirements-dev.txt`) is allowed only under `tests/property/`. Shell is POSIX `sh`, not bash.
- **Keep matchers and policy lists in sync.** Every Kiro-applicable tool in `harness/policy/risky-tools.conf` must be covered by the `matcher` regex in `.kiro/hooks/risky-tool-guard.json` (anchored `^(...)$`, exact Kiro tool IDs such as `execute_bash` or `@git/git_commit`). The validator checks this.
- **Placeholders.** Project-specific values in steering and `project-commands.env` are uppercase double-brace markers. Every marker found in tracked text files must appear in the `## Placeholders` section of `README.md` with the files that contain it; the validator reports unlisted ones and warns on stale entries. Do not introduce a new marker (including in this file) without updating that README inventory.
- **Steering files** need front matter with `inclusion: always | fileMatch | manual | auto` (`fileMatch` needs `fileMatchPattern`). Only the YAML subset in `frontmatter.py` is supported.
- **MCP (`.kiro/settings/mcp.json`).** Exact `X.Y.Z` package pins (no `@latest` or ranges), `autoApprove` limited to read-only tools, credentials only as `${ENV_VAR}` references, and each such variable documented in `.env.example` with a `# Used by MCP server: <name>` comment. Real values go in the git-ignored `.env`.
- **No secrets in tracked files.** The validator secret-scans steering, hooks, and MCP config against the patterns in `validator-config.json`.
- Hook tests launch subprocesses, so keep hook timeouts and deadlines bounded. Kiro payload fields and `ask` behavior vary by IDE version; the manual checklist in `docs/CUSTOMIZING.md` covers IDE verification.
- When behavior changes, update `docs/IMPLEMENTATION_STATUS.md` and, where relevant, `docs/CUSTOMIZING.md` and `README.md`.
