# How to write a spec and keep it traceable

1. `scripts/harness new-spec <name>` creates `.kiro/specs/<name>/` with requirements, design and tasks that pass the Spec_Linter.
2. Write acceptance criteria in EARS form (`WHEN ... THE system SHALL ...`) and give every task a `_Requirements: n.m_` line.
3. Tag each test that proves a criterion with `# Validates: <spec>/R<n>.<m>` near the top of the file or class.
4. `scripts/harness trace` prints which criteria have tests, records or neither; `scripts/validate.sh` fails on an uncovered criterion or a tag that names none.
5. Criteria that need a real Agent or a person go in a Manual_Check_Record under `docs/verification/<agent>/<version>/`, or temporarily in `docs/verification/backlog.txt`.
