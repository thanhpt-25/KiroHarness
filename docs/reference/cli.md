# Command reference

Every command is run from the repository root. `scripts/harness` is the Harness command line; the other entries are shell scripts in `scripts/`. A test (`tests/validator/test_docs_reference.py`) checks that each `scripts/harness` command lists exactly the options its `--help` prints.

Exit codes of `scripts/harness`: 0 success, 1 findings or conflicts, 2 usage or internal error.

## scripts/harness

Global option: `--root` repository root (default: the checkout containing the script).

### harness sync
Render every Generated_File from the Manifest and the sources. Options: `--check` writes nothing and exits 1 with a diff when files drifted; `--force` overwrites files that were edited by hand.

### harness mcp-inventory
Write or compare tool inventories of the pinned MCP servers. Starts the servers; needs `uvx` and network. Options: `--check` compares live tools with `harness/mcp/*.tools.json` and exits 1 on any difference; `--server` limits the run to one server (repeatable).

### harness log
Show the Decision_Log. Options: `--summary` counts each Decision per guard and the ten most frequent matched entries.

### harness new-spec
Create `.kiro/specs/<name>/` with a skeleton that passes the Spec_Linter. Argument: `name` (lowercase letters, digits and hyphens).

### harness trace
Print the Traceability_Report and write `build/traceability.json`. Options: `--json` prints the JSON report instead of Markdown. Exit 1 when the validator's trace check would report an error.

### harness doctor
Report the Harness version, Python version, `sh`, `git` and `uvx`, the enabled Agents with their protection levels, drift, and the Decision_Log status. Exit 1 when Python 3.10 or `sh` is missing, 2 when the configuration cannot be read.

### harness init
Install the Harness into another repository: copies the files, writes the Manifest with the chosen Agents, creates a README placeholder inventory and a CHANGELOG when absent, runs the Generator and the Config_Validator. Argument: `target`. Options: `--agents` comma-separated Agents to enable (kiro, claude-code, cursor, copilot; default kiro); `--force` overwrites existing files.

### harness upgrade
Update an installed Harness from a newer checkout. Files you edited are kept; a file edited by you and changed upstream is reported as a conflict with a diff and left unchanged; the Manifest is never replaced. Options: `--from` the newer checkout; `--target` the repository to upgrade (default: the repository the command runs in). Exit 1 while conflicts remain.

## Validation and test scripts

| Script | What it does |
|---|---|
| `scripts/validate.sh` | Config_Validator plus every unit test. Exit 0 only with zero errors and zero failures. |
| `scripts/validate-config.sh` | Config_Validator only. Exit 0 ok, 1 errors, 2 internal crash. |
| `scripts/test-properties.sh` | Hypothesis property suite. `HARNESS_OFFLINE=1` uses an installed Hypothesis; `HYPOTHESIS_PROFILE=ci` runs 300 examples. |
| `scripts/coverage.sh` | Coverage gate: 90 percent line and 80 percent branch. Needs `requirements-dev.txt`. |
| `scripts/mutation.sh [module ...]` | Mutation score of the guard modules (85 percent). Needs `requirements-mutation.txt`. |
| `python3 -I evals/run.py [--corpus]` | Replay eval scenarios, or the Bypass_Corpus, through every Adapter. |

## Maintenance scripts

| Script | What it does |
|---|---|
| `scripts/check-mcp-updates.sh` | Compare MCP pins with PyPI and list OSV advisories. Edits nothing. |
| `scripts/import-payloads.sh <version> [agent]` | Copy masked probe records into `tests/fixtures/payloads/<agent>/<version>/`. |
| `scripts/install-git-hooks.sh` | Set `core.hooksPath` to `.githooks`. |
| `scripts/lint.sh <file>`, `scripts/test.sh [<file>]` | Host-project lint and test commands from `scripts/project-commands.env`; exit 3 while not configured. |
