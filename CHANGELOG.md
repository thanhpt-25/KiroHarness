# Changelog

All notable changes to the Harness are recorded here, in [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format. Versions follow semantic versioning; a change to a guard's failure semantics, a Policy_File format, or the Harness_Event schema is a major version change (ADR 0010).

## [Unreleased]

### Added
- `scripts/harness init`, `upgrade` and `doctor`; `harness/VERSION` and this changelog, checked by the validator.
- Documentation organized by tutorial, how-to, reference and explanation, with command and Policy_File reference pages tested against `--help`; relative-link check; ADRs 0010 and 0011.

## [0.9.0] - 2026-11-21

### Added
- Protected-path guard, Decision_Log (`scripts/harness log --summary`), secret masking on every guard output.
- Spec_Linter, `scripts/harness new-spec`, `scripts/harness trace` and the validator trace check.
- Eval scenarios and Bypass_Corpus under `evals/`, coverage gate (`scripts/coverage.sh`) and weekly mutation job.
- Claude Code adapter: generated `.claude/settings.json`, `.mcp.json`, derived permissions; MCP tool inventories.

## [0.5.0] - 2026-11-21

### Added
- Generator (`scripts/harness sync`) with Manifest, lock file and hand-edit protection; `AGENTS.md`, Claude Code, Cursor and Copilot guidance.

## [0.3.0] - 2026-11-21

### Added
- Agent-neutral core: Harness_Event, Adapters for Kiro and Claude Code, capability matrix, `harness/bin/guard`.

## [0.2.0] - 2026-11-21

### Added
- Kiro payload probe, payload fixtures and verification records; CI workflows; ADRs 0001 to 0005.

## [0.1.0] - 2026-11-21

### Added
- Kiro harness template: steering files, seven safety hooks, pinned MCP configuration, offline validator and test suites.

[Unreleased]: https://github.com/thanhpt-25/KiroHarness/compare/0.9.0...HEAD
[0.9.0]: https://github.com/thanhpt-25/KiroHarness/releases/tag/0.9.0
