"""Hypothesis strategies for Hook_Files."""

import json

from hypothesis import strategies as st

from tests import _support  # noqa: F401  (sets sys.path)
from harness_validator.hookconfig import (
    MATCHER_REQUIRED,
    TRIGGERS,
    HookAction,
    HookDefinition,
    HookFile,
)

KNOWN_DEF_KEYS = {"name", "trigger", "matcher", "action", "timeout", "description", "enabled"}
KNOWN_ACTION_KEYS = {"type", "command", "prompt"}

# Non-ASCII, quotes, backslashes, and control characters.
tricky_text = st.text(
    alphabet=st.characters(blacklist_categories=("Cs",)) | st.sampled_from(list('"\\\n\t/\u00e9\u4e2d\U0001f600')),
    max_size=20,
)
non_empty_text = tricky_text.filter(bool)
json_scalars = st.none() | st.booleans() | st.integers(-1000, 1000) | tricky_text
json_values = st.recursive(
    json_scalars,
    lambda children: st.lists(children, max_size=3) | st.dictionaries(tricky_text, children, max_size=3),
    max_leaves=6,
)


def _extra(known):
    return st.dictionaries(
        st.text(min_size=1, max_size=8).filter(lambda k: k not in known), json_values, max_size=2
    ).map(lambda d: tuple(sorted(d.items())))


@st.composite
def hook_actions(draw):
    kind = draw(st.sampled_from(["command", "agent"]))
    return HookAction(
        type=kind,
        command=draw(st.none() | tricky_text),
        prompt=draw(st.none() | tricky_text),
        extra=draw(_extra(KNOWN_ACTION_KEYS)),
    )


@st.composite
def hook_definitions(draw):
    trigger = draw(st.sampled_from(TRIGGERS))
    if trigger in MATCHER_REQUIRED:
        matcher = draw(non_empty_text)
    else:
        matcher = draw(st.none() | tricky_text)
    return HookDefinition(
        name=draw(non_empty_text),
        trigger=trigger,
        matcher=matcher,
        action=draw(hook_actions()),
        timeout=draw(st.none() | st.integers(-5, 400)),
        description=draw(st.none() | tricky_text),
        enabled=draw(st.none() | st.booleans()),
        extra=draw(_extra(KNOWN_DEF_KEYS)),
    )


def hook_files():
    return st.builds(
        HookFile,
        version=st.just("v1"),
        hooks=st.lists(hook_definitions(), max_size=4).map(tuple),
        extra=_extra({"version", "hooks"}),
    )


def _to_obj(hook_file):
    from harness_validator.hookconfig import hook_to_obj

    return hook_to_obj(hook_file)


def _shuffle(draw, obj):
    if isinstance(obj, dict):
        items = list(obj.items())
        items = draw(st.permutations(items))
        return {k: _shuffle(draw, v) for k, v in items}
    if isinstance(obj, list):
        return [_shuffle(draw, v) for v in obj]
    return obj


@st.composite
def hook_json_texts(draw):
    """Valid Hook_File texts with random key order, indentation, and whitespace."""
    obj = _shuffle(draw, _to_obj(draw(hook_files())))
    indent = draw(st.none() | st.integers(0, 4) | st.just("\t"))
    separators = draw(st.sampled_from([(",", ":"), (", ", ": "), (" ,", " : ")]))
    ensure_ascii = draw(st.booleans())
    text = json.dumps(obj, indent=indent, separators=separators, ensure_ascii=ensure_ascii)
    lead = draw(st.sampled_from(["", " ", "\n", "\r\n", "\t\n"]))
    trail = draw(st.sampled_from(["", "\n", "\n\n", "  \r\n"]))
    return lead + text + trail
