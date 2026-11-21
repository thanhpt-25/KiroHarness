"""Guards as pure functions from a Harness_Event to a Decision (Requirement 4.1).

The matching logic lives in destructive_guard.py, risky_guard.py, and
prompt_scan.py, which also run standalone for Kiro's existing wrappers. These
functions add the agent-neutral layer on top.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import capabilities  # noqa: E402
import destructive_guard  # noqa: E402
import prompt_scan  # noqa: E402
import protected_paths  # noqa: E402
import risky_guard  # noqa: E402
from event_model import Decision, HarnessEvent, allow  # noqa: E402
from hookio import workspace_root  # noqa: E402

DESTRUCTIVE = destructive_guard.NAME
RISKY = risky_guard.NAME
PROMPT_SECRETS = prompt_scan.NAME
PROTECTED = protected_paths.NAME


def policy_dir(root=None) -> Path:
    return Path(root or workspace_root()) / "harness" / "policy"


def evaluate_destructive(event: HarnessEvent, patterns, list_path) -> Decision:
    if event.category != "shell":
        return allow(DESTRUCTIVE)
    if event.tool_id == "control_bash_process" and event.tool_input.get("action") == "stop":
        return allow(DESTRUCTIVE)
    if not isinstance(event.command, str) or not event.command.strip():
        return Decision("deny", DESTRUCTIVE, f"{DESTRUCTIVE}: command field is missing in hook input")
    matched = destructive_guard.check(event.command, patterns)
    if matched is None:
        return allow(DESTRUCTIVE)
    return Decision(
        "deny",
        DESTRUCTIVE,
        f'{DESTRUCTIVE}: blocked: matched pattern "{matched.text}"; the command is on the '
        f"Destructive_Command_List ({list_path})",
        matched.text,
    )


def evaluate_protected(event: HarnessEvent, rules, list_path) -> Decision:
    """Deny read, write and delete calls on protected paths and shell commands that read them (R11.1, R11.2)."""
    hit = None
    if event.category in ("read", "write", "delete"):
        for path in event.paths:
            rule = protected_paths.protecting_rule(rules, path)
            if rule is not None:
                hit = (path, rule)
                break
    elif event.category == "shell" and isinstance(event.command, str):
        hit = protected_paths.shell_read_target(event.command, rules)
    if hit is None:
        return allow(PROTECTED)
    path, rule = hit
    return Decision("deny", PROTECTED, f'{PROTECTED}: access to protected path "{path}" blocked (rule "{rule.text}" in {list_path})', rule.text)


def evaluate_risky(event: HarnessEvent, entries, command_fields=frozenset(), known_tool: bool = True) -> Decision:
    if event.tool_id is None:
        return allow(RISKY)
    entry = risky_guard.decide(entries, event.tool_id, event.tool_input, event.agent, event.category)
    if entry is not None:
        return Decision("ask", RISKY, risky_guard.reason_for(entry), entry.line)
    if not known_tool and event.category == "other":
        # An unmapped tool that carries a command-like field could run anything (Requirement 4.5).
        fields = sorted(f for f in command_fields if isinstance(event.tool_input.get(f), str))
        if fields:
            return Decision(
                "ask",
                RISKY,
                f"Risky tool call: {event.tool_id} is not in the {event.agent} Tool_Map and its input has "
                f"a command field ({', '.join(fields)})",
                "unmapped-tool",
            )
    return allow(RISKY)


def evaluate_prompt_secrets(event: HarnessEvent, patterns) -> Decision:
    if not event.prompt:
        return allow(PROMPT_SECRETS)
    pattern_id = prompt_scan.find_match(event.prompt, patterns)
    if pattern_id is None:
        return allow(PROMPT_SECRETS)
    return Decision(
        "deny",
        PROMPT_SECRETS,
        f'{PROMPT_SECRETS}: prompt blocked: it contains a value matching secret pattern "{pattern_id}". '
        "Remove the value and use an environment variable instead.",
        pattern_id,
    )


# --- guard registry and runner ---------------------------------------------

class PolicyLoadError(Exception):
    """A policy file could not be loaded; the message names the file."""


def _with_path(path, loader, *args):
    try:
        return loader(*args)
    except (destructive_guard.ListLoadError, risky_guard.RiskyListError, protected_paths.ProtectedListError) as exc:
        text = str(exc)
        raise PolicyLoadError(text if str(path) in text else f"{path}: {text}") from None


def _load_destructive(root):
    path = policy_dir(root) / "destructive-commands.txt"
    patterns = _with_path(path, destructive_guard.load_patterns, path)
    return lambda event: evaluate_destructive(event, patterns, path)


def _load_protected(root):
    path = policy_dir(root) / "protected-paths.txt"
    rules = _with_path(path, protected_paths.load_list, path)
    return lambda event: evaluate_protected(event, rules, path)


def _load_risky(root):
    path = policy_dir(root) / "risky-tools.conf"
    entries = _with_path(path, risky_guard.load_list, path)
    caps = capabilities.load_capabilities(root)
    command_fields = frozenset(
        m["command"] for a in caps["agents"].values() for m in a.get("tool_map", {}).values() if "command" in m
    )

    def evaluate(event):
        agent = caps["agents"].get(event.agent, {})
        known = event.tool_id in agent.get("tool_map", {}) or capabilities.classify(agent, event.tool_id)[0] != "other"
        return evaluate_risky(event, entries, command_fields, known)

    return evaluate


def _load_prompt_secrets(root):
    patterns = prompt_scan.load_patterns(prompt_scan.default_config_path())
    return lambda event: evaluate_prompt_secrets(event, patterns)


# Order matters: the first deny wins, then the first ask (event_model.combine).
GUARDS = {
    "pre_tool": (
        (DESTRUCTIVE, _load_destructive),
        (PROTECTED, _load_protected),
        (RISKY, _load_risky),
    ),
    "prompt_submit": ((PROMPT_SECRETS, _load_prompt_secrets),),
}


def guards_for(trigger: str, only=None) -> tuple:
    """Guards for ``trigger``; ``only`` (guard names) narrows the set, as the Manifest does."""
    found = GUARDS.get(trigger, ())
    return tuple(g for g in found if g[0] in only) if only is not None else found


def run_guards(trigger: str, event, error, root=None, failure=None, only=None) -> list:
    """Evaluate every guard for ``trigger`` and return one Decision per guard.

    ``event`` is the decoded Harness_Event, or None when decoding failed with
    ``error`` (a message). ``failure(guard, message)`` builds the Decision for a
    guard that cannot decide: deny for the safety guards, ask for the risky guard
    (Requirement 4.4). A guard whose policy cannot be loaded or that raises also
    gets its failure Decision, never an allow.
    """
    decisions = []
    for name, loader in guards_for(trigger, only):
        if event is None:
            decisions.append(failure(name, f"hook input could not be parsed (parse error): {error}"))
            continue
        try:
            evaluate = loader(root)
        except (PolicyLoadError, destructive_guard.ListLoadError, risky_guard.RiskyListError, prompt_scan.PatternLoadError, protected_paths.ProtectedListError,
               capabilities.CapabilityError) as exc:
            decisions.append(failure(name, f"policy could not be loaded: {exc}"))
            continue
        try:
            decisions.append(evaluate(event))
        except Exception as exc:  # a guard bug must not turn into an allow
            decisions.append(failure(name, f"guard crashed: {exc.__class__.__name__}: {exc}"))
    return decisions
