# Documentation

Organized by what you are trying to do. Every document in `docs/` is linked from this page; a test checks that.

## Tutorials (learn)
- [Install the Harness and see a guard block a command](tutorials/getting-started.md)

## How-to guides (get something done)
- [Install and upgrade the Harness](how-to/install-and-upgrade.md)
- [Hướng dẫn sử dụng (tiếng Việt)](HUONG_DAN_SU_DUNG.md): cài đặt, steering, hook, MCP, validator, lint và test
- [Enable another Agent](how-to/enable-an-agent.md)
- [Write a spec and keep it traceable](how-to/write-a-spec.md)
- [Run the evals and quality gates](how-to/run-evals-and-gates.md)
- [Customization Guide](CUSTOMIZING.md): steering files, hooks, guard lists, MCP servers, the Manifest, CI, manual checklist
- [Git hooks](GIT_HOOKS.md)

## Reference (look something up)
- [Command reference](reference/cli.md)
- [Policy_File formats](reference/policy-files.md)
- [Capability matrix](reference/capabilities.md) (generated)

## Explanation (understand why)
- [Architecture](explanation/architecture.md)
- [Why the guards are a safety net, not a sandbox](explanation/limits-and-threat-model.md)
- [Project overview](PROJECT_OVERVIEW.md)
- [Architecture Decision Records](adr/README.md)
- [Implementation status](IMPLEMENTATION_STATUS.md)

## Verification evidence
- [Claude Code runbook](verification/claude-code/RUNBOOK.md), [Kiro runbook](verification/kiro/RUNBOOK.md); recorded checks live under `docs/verification/<agent>/<version>/`.
- [Verification conventions](verification/README.md) and the [record template](verification/TEMPLATE.md)
