---
inclusion: manual
---

# Release Checklist

Include this file in a chat with `#release-checklist` when preparing a release.

1. `scripts/validate.sh` exits with code 0.
2. The full test suite passes in single-run mode.
3. The changelog lists every user-visible change since {{LAST_RELEASE_TAG}}.
4. Version numbers are updated in every place the project declares them.
5. `scripts/check-mcp-updates.sh` has been run and any MCP pin bumps reviewed.
6. Ask the user to confirm before tagging, publishing, or deploying.

## Harness Release Gates

A release of a project that ships this Harness also needs:

7. CI is green on the full matrix for the commit to tag.
8. `scripts/harness trace` prints a Traceability_Report with zero errors.
9. Manual_Check_Records are no older than 30 days for each Agent whose protection is marked "enforced".
10. `harness/VERSION` and the CHANGELOG entry match the release tag.
