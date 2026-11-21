---
inclusion: fileMatch
fileMatchPattern: ["**/*.test.*", "**/*.spec.*", "**/test_*.py", "**/*_test.go"]
---

# Testing Standards

- Test framework: {{TEST_FRAMEWORK}}.
- Run tests in single-run mode, never watch mode. The commands are in
  `scripts/project-commands.env`; `scripts/test.sh` runs them.
- Each test checks one behavior and has a name that states it.
- Test behavior through public interfaces, not private helpers.
- Do not mock what you can run cheaply. Mock network calls and the clock.
- A bug fix starts with a test that fails before the fix.
- Do not delete or weaken a failing test to make a change pass; report it.
