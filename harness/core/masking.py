"""Secret masking shared by every output channel (agent-harness-platform R11.4).

A match of a secret pattern keeps its first 4 characters; the rest becomes ``*``
(Template spec Requirement 10.6).
"""

from __future__ import annotations


def mask_value(value: str) -> str:
    return value[:4] + "*" * max(len(value) - 4, 0)


def mask_secrets(text: str, patterns) -> str:
    for _pattern_id, regex in patterns:
        text = regex.sub(lambda m: mask_value(m.group(0)), text)
    return text
