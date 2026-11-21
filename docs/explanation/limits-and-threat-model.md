# Why the guards are a safety net, not a sandbox

The guards stop an agent that makes an ordinary mistake: a force push, a `.env` read, a pasted key. They match patterns in the command text. Anyone who controls the text can write it in a form no pattern predicts (quote splitting, encoded pipelines, another interpreter), so they do not contain a hostile agent.

`evals/bypass-corpus.json` measures this instead of claiming it: each obfuscated form is labelled `must-block`, `known-gap` or `safe`, and a run fails when any label stops being true. The categories of known gaps are listed in the [Customization Guide](../CUSTOMIZING.md#known-gaps-and-limits). For untrusted workloads use OS-level isolation: a container or VM with no credentials and no network you do not intend.

Defense is layered where an Agent allows: hooks see the arguments, permission rules still hold when a hook is off, and guidance shapes behavior before a tool is called ([ADR 0006](../adr/0006-agent-neutral-core-layout.md), [ADR 0008](../adr/0008-claude-code-adapter-and-mcp-inventory.md), [ADR 0009](../adr/0009-protection-traceability-and-evals.md)). Failure semantics differ on purpose: destructive, prompt-secret and protected-path guards fail closed; the risky-tool guard fails to ask.
