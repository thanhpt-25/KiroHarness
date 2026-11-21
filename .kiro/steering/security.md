---
inclusion: always
---

# Security Rules

## Least Privilege

- Request only the permissions, scopes, and tools a task needs.
- Do not add tools to an MCP server's `autoApprove` list unless they are
  read-only. Do not widen IAM policies, file permissions, or network access to
  make an error go away; explain the error instead.

## Secrets Through Environment Variables

- Never write a credential, token, password, or key into a file in this
  repository, a prompt, a log, or a test fixture.
- Read secrets from environment variables. In `.kiro/settings/mcp.json`, use a
  Secret_Reference such as `${VAR_NAME}` and add the variable to `.env.example`
  with a placeholder value.
- `.env` is local only and must not be committed.

## Input Validation at Trust Boundaries

- Validate and constrain all input that crosses a trust boundary: HTTP
  requests, CLI arguments, files, environment variables, and tool output.
- Use parameterized queries. Quote or escape values before putting them in
  shell commands, file paths, or templates.

## Confirm Before Destructive Actions

- Ask before deleting files or data, rewriting git history, force-pushing,
  deploying, publishing, or changing permissions.
- The Destructive_Command_Guard hook blocks commands on
  `harness/policy/destructive-commands.txt`. Do not try to work around a
  block; tell the user what was blocked and why.
