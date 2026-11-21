---
inclusion: fileMatch
fileMatchPattern: "**/*.{ts,tsx,js,jsx,py,go}"
---

# Coding Standards

- Follow the conventions already in the file you are editing. Where the code
  base is silent, use the idiomatic style for {{PRIMARY_LANGUAGE}}.
- Formatter and linter: the lint command in `scripts/project-commands.env`.
  The Quality_Hook runs it on every saved source file; fix what it reports.
- Prefer small functions with one job and names that say what they do.
- Handle errors explicitly. Do not swallow exceptions or ignore returned errors.
- Do not leave commented-out code, debug prints, or TODOs without an issue link.
- Keep public interfaces documented with a short comment or docstring.
