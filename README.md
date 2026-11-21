# Kiro Agent Harness Template

A starter harness for Kiro IDE projects. Copy it into a repository to get
steering files that give the agent project context, hooks that block
destructive commands and ask before risky tool calls, lint and test checks on
save, a workspace MCP configuration, an example spec, and a validator that
checks all of it.

## Directory Layout

| Directory | What it holds |
|---|---|
| `.kiro/steering/` | Markdown Steering_Files with front matter. They configure the **steering** context the agent loads: product, tech, structure, security, coding standards, testing, and example `manual` and `auto` files. |
| `.kiro/hooks/` | v1 Hook_Files (`*.json`). They configure the **hooks**: the destructive command guard, the risky tool guard, the quality check on save, and session, prompt, task, and stop hooks. |
| `.kiro/hooks/scripts/` | The Hook_Scripts that the **hooks** run, their Python logic in `lib/`, and the guard lists `destructive-commands.txt` and `risky-tools.conf`. |
| `.kiro/hooks/examples/` | Disabled example Hook_Files for the **hooks**. See `docs/CUSTOMIZING.md` to enable them. |
| `.kiro/settings/` | `mcp.json`, the workspace **MCP configuration** for the AWS documentation, fetch, and git servers. |
| `.kiro/specs/` | Feature **specs**. Each spec directory holds `requirements.md`, `design.md`, and `tasks.md`. |
| `.kiro/specs/example-feature/` | An example **spec** showing the expected format of the three spec documents. |
| `.githooks/` | Optional repository-managed Git hooks for validation, commit messages, and pre-push property tests. |
| `scripts/` | The **scripts**: `validate.sh`, the Config_Validator, lint/test commands, and the opt-in Git hook installer. |
| `docs/` | **Documentation**: `CUSTOMIZING.md` explains harness configuration; `GIT_HOOKS.md` explains the managed hooks. |

## Setup

1. Copy the Template into the target repository:
   ```sh
   cp -R kiro-agent-harness-template/. /path/to/your-repo/
   ```
2. Copy `.env.example` to `.env`:
   ```sh
   cp .env.example .env
   ```
3. Replace every `{{PLACEHOLDER_NAME}}` value listed under
   [Placeholders](#placeholders), and every placeholder value in `.env`. To
   find what is left:
   ```sh
   grep -rnE '\{\{[A-Z][A-Z0-9_]*\}\}' .kiro scripts docs
   ```
4. In `.kiro/settings/mcp.json`, set `disabled` to `false` for each MCP server
   you want to use.
5. Run the validation command:
   ```sh
   scripts/validate.sh
   ```
6. Optionally enable the repository-managed Git hooks:
   ```sh
   scripts/install-git-hooks.sh
   ```
   This sets `core.hooksPath` in this repository's local Git config. The
   pre-push hook requires the development dependency from
   `requirements-dev.txt` to already be installed. See
   [Git Hook Implementation Best Practices](docs/GIT_HOOKS.md).

`.env` holds your real credentials and must not be committed. `.gitignore`
already ignores it.

Expected result of step 5: the command exits with code 0 and prints a summary
with the number of files checked, for example:

```text
Summary: 52 files checked, 0 errors, 0 warnings
Validation: 52 files checked, 0 warnings; Tests: 68 passed, 0 failed
```

Python 3.10 or newer is required. `uv` is required to start the MCP servers.

## Maintainer Commands

- `scripts/test-properties.sh` runs the Hypothesis property tests. Run it
  after changing validator or guard code.
- `scripts/install-git-hooks.sh` opts this clone into `.githooks/`; it does
  not change global Git configuration.
- `scripts/check-mcp-updates.sh` compares the MCP version pins with PyPI. It
  needs network access and changes no files.

## Placeholders

Each item gives the placeholder, the files that contain it, and the value to
supply.

- `{{PLACEHOLDER_NAME}}` — `.kiro/specs/kiro-agent-harness-template/requirements.md`, `.kiro/specs/kiro-agent-harness-template/design.md`, `.kiro/specs/kiro-agent-harness-template/tasks.md`, `docs/CUSTOMIZING.md`, `docs/PROJECT_OVERVIEW.md` — nothing to replace; the notation example used in the docs and spec files.
- `{{NAME}}` — `.kiro/specs/kiro-agent-harness-template/design.md`, `.kiro/specs/kiro-agent-harness-template/tasks.md` — nothing to replace; notation used in the Template's own spec.
- `{{WORKSPACE_ROOT}}` — `.kiro/specs/kiro-agent-harness-template/design.md` — nothing to replace; a fallback described in the Template's own design.
- `{{PROJECT_NAME}}` — `.kiro/steering/product.md`, `.kiro/specs/kiro-agent-harness-template/design.md` — the name of your project.
- `{{PRODUCT_SUMMARY}}` — `.kiro/steering/product.md` — one sentence on what the product does.
- `{{TARGET_USERS}}` — `.kiro/steering/product.md` — who the primary users are.
- `{{PRIMARY_LANGUAGE}}` — `.kiro/steering/tech.md`, `.kiro/steering/coding-standards.md`, `.kiro/specs/kiro-agent-harness-template/design.md` — the main programming language.
- `{{PACKAGE_MANAGER}}` — `.kiro/steering/tech.md`, `.kiro/specs/kiro-agent-harness-template/design.md` — the package manager, such as npm, uv, or go modules.
- `{{SOURCE_DIR}}` — `.kiro/steering/structure.md` — the directory that holds application source code.
- `{{TEST_DIR}}` — `.kiro/steering/structure.md` — the directory that holds tests.
- `{{TEST_FRAMEWORK}}` — `.kiro/steering/testing.md` — the test framework, such as pytest or Vitest.
- `{{API_STYLE}}` — `.kiro/steering/api-design.md` — the API style, such as REST with JSON or gRPC.
- `{{LAST_RELEASE_TAG}}` — `.kiro/steering/release-checklist.md` — how to find the previous release tag, such as "the latest v* git tag".
- `{{LINT_FILE_COMMAND}}` — `scripts/project-commands.env`, `.kiro/specs/kiro-agent-harness-template/design.md` — the command that lints one file; the path is appended.
- `{{TEST_FILE_COMMAND}}` — `scripts/project-commands.env`, `.kiro/specs/kiro-agent-harness-template/design.md` — the command that runs one test file once, without watch mode; the path is appended.
- `{{TEST_COMMAND}}` — `scripts/project-commands.env`, `.kiro/specs/kiro-agent-harness-template/design.md` — the command that runs the full test suite once, without watch mode.
