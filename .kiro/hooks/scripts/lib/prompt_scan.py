"""UserPromptSubmit hook: block prompts that contain a literal secret.

Uses ``secret_patterns`` from scripts/validator-config.json, the same list the
Config_Validator uses. Exit 2 blocks the prompt; the matched value is never
printed. Exit 2 also when the pattern file cannot be loaded (fails closed).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hookio import HookInputError, parse_hook_input, workspace_root  # noqa: E402

NAME = "prompt-secret-scan"
MAX_INPUT_BYTES = 1_048_576


class PatternLoadError(Exception):
    pass


def default_config_path() -> Path:
    return workspace_root() / "scripts" / "validator-config.json"


def load_patterns(path) -> list:
    """Return ``[(id, compiled regex), ...]``."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        items = data["secret_patterns"]
        if not isinstance(items, list) or not items:
            raise ValueError("secret_patterns must be a non-empty list")
        return [(item["id"], re.compile(item["regex"])) for item in items]
    except (OSError, UnicodeDecodeError, ValueError, KeyError, TypeError, re.error) as exc:
        raise PatternLoadError(f"could not load secret patterns from {path}: {exc}") from None


def find_match(prompt: str, patterns):
    for pattern_id, regex in patterns:
        if regex.search(prompt):
            return pattern_id
    return None


def prompt_text(data: bytes):
    """The prompt from the hook JSON, or the raw input when it is not JSON."""
    try:
        hook_input = parse_hook_input(data)
    except HookInputError:
        text = data.decode("utf-8", "replace")
        return text if text.strip() else None
    return hook_input.prompt


def main(stdin, stderr, config_path=None) -> int:
    config_path = Path(config_path) if config_path else default_config_path()
    try:
        patterns = load_patterns(config_path)
    except PatternLoadError as exc:
        stderr.write(f"{NAME}: {exc}; blocking the prompt because it could not be scanned\n")
        return 2
    prompt = prompt_text(stdin.read(MAX_INPUT_BYTES))
    if not prompt:
        return 0
    pattern_id = find_match(prompt, patterns)
    if pattern_id is None:
        return 0
    stderr.write(
        f'{NAME}: prompt blocked: it contains a value matching secret pattern "{pattern_id}". '
        "Remove the value and use an environment variable instead.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.stdin.buffer, sys.stderr))
