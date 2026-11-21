# How to install and upgrade the Harness

## Install
Run `scripts/harness init <target-dir> --agents kiro,claude-code` from a checkout of the Harness. See the [command reference](../reference/cli.md#harness-init). Commit the result, including the generated files and `harness/release.lock.json`.

## Upgrade
1. Get the newer Harness checkout somewhere, for example `../harness-new`.
2. In your repository run `scripts/harness upgrade --from ../harness-new`.
3. Files you never edited are updated. Files you edited are kept. If a file you edited also changed upstream, it is listed as a conflict with a diff and left unchanged; merge it by hand and run the command again. The Manifest is never replaced.
4. Run `scripts/validate.sh` and read the new entries in the [CHANGELOG](../../CHANGELOG.md).

A major version change means a guard's failure semantics, a Policy_File format, or the Harness_Event schema changed; read the CHANGELOG before upgrading across one ([ADR 0010](../adr/0010-versioning-policy.md)).
