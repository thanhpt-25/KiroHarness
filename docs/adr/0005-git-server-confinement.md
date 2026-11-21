# 0005. Git MCP server confinement with `--repository .`

- Status: Accepted, pending IDE check
- Date: 2026-11-21
- Criteria: kiro-agent-harness-template/R8.8

## Context

Requirement 8.8 requires the git MCP server to operate only on the workspace
repository. `mcp-server-git` takes `--repository <path>`. The Template ships
`--repository .`, which is correct only if Kiro starts MCP servers with the
workspace root as the working directory. An absolute path would be safer but
cannot be committed to a reusable template.

## Decision

Keep `--repository .` and a pinned `mcp-server-git` version at or above the
minimum in `scripts/validator-config.json` (2026.10.28, which fixes the known
confinement escapes). Document the absolute-path alternative in
`docs/CUSTOMIZING.md`.

## Consequences

- The confinement depends on Kiro's MCP working directory, which is not yet
  verified on a real IDE build.
- The platform plan verifies it as a Manual_Check_Record
  (agent-harness-platform/R3.4) and through the integration suite's
  `git_status` check.

## Verification

Pending: `tests/integration/test_mcp_servers.py` with `HARNESS_INTEGRATION=1`,
and the manual Kiro check in agent-harness-platform Task 5.1.
