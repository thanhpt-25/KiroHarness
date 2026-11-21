# Reference Kiro payloads

These payloads are written by hand from the documented Kiro IDE 1.x hook
format (snake_case fields; see the Template design, Research Findings). They
are **not** recordings. They keep the fixture tests running until payloads
recorded from a real Kiro build are imported with
`scripts/import-payloads.sh <kiro-version>` into a sibling directory.

`/WORKSPACE` stands for the workspace root. A `<name>.expect.json` file next
to a payload pins the exact outcome for each hook that receives it.
