---
inclusion: manual
---

# Spec Workflow

Use this for any feature or change that needs more than a small edit. Agents
without a built-in spec mode follow it by hand.

1. **Requirements.** Create `.kiro/specs/<name>/requirements.md` (run
   `scripts/harness new-spec <name>`). Write a user story and numbered
   acceptance criteria. Each criterion starts with THE, WHEN, WHILE, IF or WHERE
   and says what SHALL happen. Ask the user to confirm before continuing.
2. **Design.** Write `design.md` with Overview, Architecture, Components and
   Interfaces, Data Models, Error Handling and Testing Strategy. State each
   decision and the criteria it serves. Ask the user to confirm.
3. **Tasks.** Write `tasks.md` as a checklist of small steps. End each task with
   `_Requirements: <n.m>, ..._` naming the criteria it implements.
4. **Implement with tests.** Work one task at a time. Write the test first, tag
   it with `# Validates: <spec>/R<n>.<m>`, make it pass, then tick the task.
5. **Check.** Run `scripts/validate.sh`. It lints every spec and reports criteria
   that no task references and tests whose tag names a missing criterion.

Do not start implementing before the requirements and design are confirmed.
