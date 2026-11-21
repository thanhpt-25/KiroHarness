# 0010. Versioning policy

- Status: Accepted
- Date: 2026-11-21
- Criteria: agent-harness-platform/R17.1, agent-harness-platform/R16.5

## Context
Projects copy the Harness and upgrade it later. They need to know when an upgrade can change what is blocked or how their own policy files are read.

## Decision
`harness/VERSION` holds a semantic version. A **major** version change is any change to a guard's failure semantics (fail closed, fail to ask), a Policy_File format, or the Harness_Event schema. A **minor** change adds a guard, an Agent, a command or an option without changing those. A **patch** change fixes a defect without changing documented behavior. Every version has a `## [x.y.z]` heading in `CHANGELOG.md`, and the Config_Validator reports an error when it is missing.

## Consequences
Adding a new deny pattern to the shipped policy files is a minor change even though it blocks more; tightening what an existing guard does when its policy is unreadable is major. `harness upgrade` keeps edited policy files, so a new shipped pattern reaches only unedited copies.

## Verification
`tests/validator/test_release_checks.py`.
