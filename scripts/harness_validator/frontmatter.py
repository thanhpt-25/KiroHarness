"""The YAML subset used by steering front matter, without a YAML library.

Supported: ``key: value`` lines with plain, single-quoted, or double-quoted
scalars; ``true``/``false``; flow sequences of scalars (``[a, "b"]``); block
sequences (``- a``); and ``#`` comments. Anything else (nested mappings,
anchors, aliases, tags, multi-line scalars, tab indentation) is rejected.
"""

from __future__ import annotations

import re

_KEY_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*)\s*:(?:[ ](.*))?$")
_BOOLS = {"true": True, "True": True, "TRUE": True, "false": False, "False": False, "FALSE": False}
_PLAIN_BAD_START = set("-?:,[]{}#&*!|>'\"%@`")
_DQ_ESCAPES = {
    '"': '"',
    "\\": "\\",
    "/": "/",
    "n": "\n",
    "t": "\t",
    "r": "\r",
    "0": "\0",
    "b": "\b",
    "f": "\f",
    "e": "\x1b",
    " ": " ",
    "N": "\x85",
    "_": "\xa0",
    "L": "\u2028",
    "P": "\u2029",
}
_HEX_ESCAPES = {"x": 2, "u": 4, "U": 8}


class FrontMatterError(Exception):
    def __init__(self, line: int, msg: str):
        super().__init__(f"line {line}: {msg}")
        self.line = line
        self.msg = msg


def split_front_matter(text: str):
    """Return ``(yaml_text, body)`` or ``None`` when the text has no ``---`` block."""
    if text.startswith("\ufeff"):
        text = text[1:]
    lines = text.split("\n")
    if not lines or lines[0].rstrip("\r").rstrip() != "---":
        return None
    for index in range(1, len(lines)):
        if lines[index].rstrip("\r").rstrip() == "---":
            yaml_text = "\n".join(lines[1:index])
            body = "\n".join(lines[index + 1 :])
            return yaml_text, body
    return None


def _strip_comment(rest: str, line_no: int) -> None:
    rest = rest.strip()
    if rest and not rest.startswith("#"):
        raise FrontMatterError(line_no, f"unexpected text after value: {rest!r}")


def _parse_double(s: str, start: int, line_no: int):
    """Parse a double-quoted scalar starting at ``s[start] == '"'``. Return (value, end)."""
    out = []
    i = start + 1
    while i < len(s):
        ch = s[i]
        if ch == '"':
            return "".join(out), i + 1
        if ch == "\\":
            if i + 1 >= len(s):
                break
            esc = s[i + 1]
            if esc in _DQ_ESCAPES:
                out.append(_DQ_ESCAPES[esc])
                i += 2
                continue
            if esc in _HEX_ESCAPES:
                width = _HEX_ESCAPES[esc]
                digits = s[i + 2 : i + 2 + width]
                if len(digits) != width or not re.fullmatch(r"[0-9A-Fa-f]+", digits):
                    raise FrontMatterError(line_no, f"bad \\{esc} escape in double-quoted string")
                code = int(digits, 16)
                if code > 0x10FFFF or 0xD800 <= code <= 0xDFFF:
                    raise FrontMatterError(line_no, "escape is not a valid character")
                out.append(chr(code))
                i += 2 + width
                continue
            raise FrontMatterError(line_no, f"unknown escape \\{esc} in double-quoted string")
        out.append(ch)
        i += 1
    raise FrontMatterError(line_no, "unterminated double-quoted string (multi-line scalars are not supported)")


def _parse_single(s: str, start: int, line_no: int):
    out = []
    i = start + 1
    while i < len(s):
        ch = s[i]
        if ch == "'":
            if i + 1 < len(s) and s[i + 1] == "'":
                out.append("'")
                i += 2
                continue
            return "".join(out), i + 1
        out.append(ch)
        i += 1
    raise FrontMatterError(line_no, "unterminated single-quoted string (multi-line scalars are not supported)")


def _plain(text: str, line_no: int, in_flow: bool):
    value = text.strip()
    if value == "":
        raise FrontMatterError(line_no, "empty value")
    if value[0] in _PLAIN_BAD_START and not (value[0] in "-?:" and len(value) > 1 and value[1] not in " \t"):
        if value[0] in "&*":
            raise FrontMatterError(line_no, "anchors and aliases are not supported")
        if value[0] == "!":
            raise FrontMatterError(line_no, "tags are not supported")
        if value[0] in "|>":
            raise FrontMatterError(line_no, "multi-line scalars are not supported")
        if value[0] == "{":
            raise FrontMatterError(line_no, "nested mappings are not supported")
        raise FrontMatterError(line_no, f"value cannot start with {value[0]!r} unquoted")
    if ": " in value or value.endswith(":"):
        raise FrontMatterError(line_no, "nested mappings are not supported")
    if in_flow and any(c in value for c in "[]{}"):
        raise FrontMatterError(line_no, "nested collections are not supported")
    if value in _BOOLS:
        return _BOOLS[value]
    return value


def _scalar(rest: str, line_no: int):
    """Parse a complete scalar (with an optional trailing comment)."""
    s = rest.strip()
    if s.startswith('"'):
        value, end = _parse_double(s, 0, line_no)
        _strip_comment(s[end:], line_no)
        return value
    if s.startswith("'"):
        value, end = _parse_single(s, 0, line_no)
        _strip_comment(s[end:], line_no)
        return value
    if s.startswith("["):
        return _flow(s, line_no)
    return _plain(_cut_comment(s), line_no, in_flow=False)


def _cut_comment(s: str) -> str:
    match = re.search(r"(^|\s)#", s)
    return s[: match.start()] if match else s


def _flow(s: str, line_no: int) -> list:
    items = []
    i = 1
    expecting_item = True
    while True:
        while i < len(s) and s[i] in " \t":
            i += 1
        if i >= len(s):
            raise FrontMatterError(line_no, "unterminated flow sequence (multi-line values are not supported)")
        ch = s[i]
        if ch == "]":
            if expecting_item and items:
                raise FrontMatterError(line_no, "empty item in flow sequence")
            _strip_comment(s[i + 1 :], line_no)
            return items
        if not expecting_item:
            if ch != ",":
                raise FrontMatterError(line_no, "expected ',' or ']' in flow sequence")
            i += 1
            expecting_item = True
            continue
        if ch == ",":
            raise FrontMatterError(line_no, "empty item in flow sequence")
        if ch == '"':
            value, i = _parse_double(s, i, line_no)
        elif ch == "'":
            value, i = _parse_single(s, i, line_no)
        elif ch in "[{":
            raise FrontMatterError(line_no, "nested collections are not supported")
        else:
            j = i
            while j < len(s) and s[j] not in ",]":
                j += 1
            value = _plain(s[i:j], line_no, in_flow=True)
            if not isinstance(value, str):
                raise FrontMatterError(line_no, "flow sequence items must be strings")
            i = j
        if not isinstance(value, str):
            raise FrontMatterError(line_no, "flow sequence items must be strings")
        items.append(value)
        expecting_item = False


def parse_front_matter(yaml_text: str) -> dict:
    """Parse the supported YAML subset. Raise FrontMatterError(line, msg) otherwise."""
    data = {}
    lines = yaml_text.split("\n")
    current_list_key = None
    for index, raw in enumerate(lines):
        line_no = index + 1
        line = raw.rstrip("\r")
        if line.strip() == "" or line.strip().startswith("#"):
            continue
        indent = line[: len(line) - len(line.lstrip(" \t"))]
        if "\t" in indent:
            raise FrontMatterError(line_no, "tab indentation is not supported")
        body = line.strip()
        if body.startswith("-") and (body == "-" or body[1] in " \t"):
            if current_list_key is None:
                raise FrontMatterError(line_no, "sequence item without a key")
            item_text = body[1:].strip()
            if item_text == "" or _cut_comment(item_text).strip() == "":
                raise FrontMatterError(line_no, "empty sequence item (nested values are not supported)")
            value = _scalar(item_text, line_no)
            if not isinstance(value, str):
                raise FrontMatterError(line_no, "sequence items must be strings")
            data[current_list_key].append(value)
            continue
        if indent:
            raise FrontMatterError(line_no, "nested mappings and multi-line scalars are not supported")
        match = _KEY_RE.match(line)
        if not match:
            if body.startswith(("&", "*", "!", "?", "{", "[", "|", ">")):
                raise FrontMatterError(line_no, "unsupported YAML construct")
            raise FrontMatterError(line_no, "expected 'key: value'")
        key, rest = match.group(1), match.group(2)
        if key in data:
            raise FrontMatterError(line_no, f"duplicate key {key!r}")
        if current_list_key is not None and data[current_list_key] == []:
            data[current_list_key] = ""
        current_list_key = None
        if rest is None or _cut_comment(rest).strip() == "":
            data[key] = []
            current_list_key = key
            continue
        data[key] = _scalar(rest, line_no)
    if current_list_key is not None and data[current_list_key] == []:
        data[current_list_key] = ""
    return data


# --- dumping -------------------------------------------------------------


def _needs_quotes(value: str, in_flow: bool) -> bool:
    if value == "" or value != value.strip():
        return True
    if value in _BOOLS or value[0] in _PLAIN_BAD_START:
        return True
    if ": " in value or value.endswith(":") or " #" in value or "\t#" in value:
        return True
    if in_flow and any(c in value for c in ",[]{}"):
        return True
    if any(ord(c) < 0x20 or c in "\x7f\x85\u2028\u2029\ufeff" for c in value):
        return True
    return False


def _quote(value: str) -> str:
    out = ['"']
    for ch in value:
        if ch == '"':
            out.append('\\"')
        elif ch == "\\":
            out.append("\\\\")
        elif ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif ch == "\r":
            out.append("\\r")
        elif ord(ch) < 0x20 or ch in "\x7f\x85\u2028\u2029\ufeff":
            out.append(f"\\u{ord(ch):04x}")
        else:
            out.append(ch)
    out.append('"')
    return "".join(out)


def _dump_scalar(value: str, in_flow: bool = False) -> str:
    return _quote(value) if _needs_quotes(value, in_flow) else value


def dump_front_matter(data: dict) -> str:
    """Dump a mapping of str/bool/list[str] values in the supported subset."""
    lines = []
    for key, value in data.items():
        if not isinstance(key, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_-]*", key):
            raise ValueError(f"unsupported key {key!r}")
        if isinstance(value, bool):
            lines.append(f"{key}: {'true' if value else 'false'}")
        elif isinstance(value, str):
            lines.append(f"{key}: {_dump_scalar(value)}")
        elif isinstance(value, (list, tuple)):
            if not all(isinstance(v, str) for v in value):
                raise ValueError(f"list values must be strings for key {key!r}")
            items = ", ".join(_dump_scalar(v, in_flow=True) for v in value)
            lines.append(f"{key}: [{items}]")
        else:
            raise ValueError(f"unsupported value type for key {key!r}")
    return "\n".join(lines) + ("\n" if lines else "")
