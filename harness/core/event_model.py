"""Agent-neutral event and decision model (agent-harness-platform Requirement 4.1).

A Harness_Event is what a guard sees; a Decision is what it returns. Guards are
pure functions from one to the other, so they can be tested without
subprocesses and shared by every Agent through its Adapter.
"""

from __future__ import annotations

from dataclasses import dataclass, field

SCHEMA_VERSION = 1
CATEGORIES = ("shell", "read", "write", "delete", "web", "mcp", "spec", "other")
TRIGGERS = (
    "session_start",
    "prompt_submit",
    "pre_tool",
    "post_tool",
    "file_saved",
    "file_created",
    "file_deleted",
    "task_done",
    "stop",
    "pre_compact",
)
DECISION_KINDS = ("allow", "ask", "deny")


@dataclass(frozen=True)
class HarnessEvent:
    agent: str
    trigger: str
    tool_id: object = None  # native tool ID, e.g. "execute_bash", "Bash", "@git/git_commit"
    category: object = None  # one of CATEGORIES, or None when there is no tool
    command: object = None
    paths: tuple = ()
    url: object = None
    prompt: object = None
    tool_input: dict = field(default_factory=dict)
    cwd: object = None
    schema: int = SCHEMA_VERSION

    def __post_init__(self):
        if self.trigger not in TRIGGERS:
            raise ValueError(f"unknown trigger {self.trigger!r}")
        if self.category is not None and self.category not in CATEGORIES:
            raise ValueError(f"unknown category {self.category!r}")


@dataclass(frozen=True)
class Decision:
    kind: str
    guard: str
    reason: str = ""
    matched: object = None  # the policy entry text that decided; never a secret value
    stderr: str = ""  # extra diagnostics for the developer (not shown to the model)

    def __post_init__(self):
        if self.kind not in DECISION_KINDS:
            raise ValueError(f"unknown decision kind {self.kind!r}")


def allow(guard: str) -> Decision:
    return Decision("allow", guard)


def combine(decisions) -> Decision:
    """First deny wins, otherwise the first ask, otherwise allow (Requirement 4.7)."""
    decisions = list(decisions)
    for kind in ("deny", "ask"):
        for decision in decisions:
            if decision.kind == kind:
                return decision
    return decisions[0] if decisions else Decision("allow", "none")
