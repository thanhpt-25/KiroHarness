"""Payload probe: save the raw hook payload Kiro sends, masked, for fixtures.

Used only by the disabled example hook ``.kiro/hooks/examples/payload-probe.json``
(agent-harness-platform Requirement 3.1). The probe never blocks: it always
exits 0 and writes nothing to standard output, so enabling it cannot change
what the agent is allowed to do.

Masking (Requirement 11.4): every match of a secret pattern from
scripts/validator-config.json keeps its first 4 characters and the rest
becomes ``*``. The workspace root is replaced by ``/WORKSPACE`` and the home
directory by ``/HOME``, so recorded files carry no machine paths.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from hookio import MAX_INPUT_BYTES, workspace_root  # noqa: E402
from prompt_scan import PatternLoadError, default_config_path, load_patterns  # noqa: E402

NAME = "payload-probe"
TRIGGER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,63}$")
WORKSPACE_TOKEN = "/WORKSPACE"
HOME_TOKEN = "/HOME"


def mask_value(value: str) -> str:
    return value[:4] + "*" * max(len(value) - 4, 0)


def mask_secrets(text: str, patterns) -> str:
    for _pattern_id, regex in patterns:
        text = regex.sub(lambda m: mask_value(m.group(0)), text)
    return text


def normalize_paths(text: str, root: Path, home) -> str:
    # Longest first, so a workspace inside the home directory maps to /WORKSPACE.
    replacements = [(str(root), WORKSPACE_TOKEN)]
    if home:
        replacements.append((str(home), HOME_TOKEN))
    for original, token in sorted(replacements, key=lambda item: len(item[0]), reverse=True):
        if original and original != "/":
            text = text.replace(original, token)
            text = text.replace(json.dumps(original)[1:-1], token)  # JSON-escaped form
    return text


def sanitize(data: bytes, patterns, root: Path, home) -> str:
    text = data.decode("utf-8", "replace")
    return normalize_paths(mask_secrets(text, patterns), root, home)


def probe_dir(root: Path) -> Path:
    return root / ".harness" / "probe"


def write_record(text: str, trigger: str, root: Path, now=None) -> Path:
    target_dir = probe_dir(root) / trigger
    target_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime(now))
    for counter in range(1000):
        path = target_dir / f"{stamp}-{counter:03d}.json"
        try:
            with open(path, "x", encoding="utf-8") as handle:
                handle.write(text)
            return path
        except FileExistsError:
            continue
    raise OSError(f"too many probe records for {stamp}")


VERSION_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._-]{0,31}$")


def fixture_dir(root: Path, version: str) -> Path:
    return root / "tests" / "fixtures" / "payloads" / "kiro" / version


def import_records(root: Path, version: str, patterns, stdout, stderr) -> int:
    """Copy probe records into the fixture tree. Return the process exit code."""
    if not VERSION_RE.match(version):
        stderr.write(f"{NAME}: invalid Kiro version {version!r}\n")
        return 2
    source = probe_dir(root)
    records = sorted(source.glob("*/*.json")) if source.is_dir() else []
    if not records:
        stderr.write(f"{NAME}: no probe records in {source}\n")
        return 1
    copied = skipped = 0
    for record in records:
        text = record.read_text(encoding="utf-8", errors="replace")
        try:
            json.loads(text)
        except ValueError:
            stderr.write(f"{NAME}: skipping {record.name}: not valid JSON\n")
            skipped += 1
            continue
        text = sanitize(text.encode("utf-8"), patterns, root, os.environ.get("HOME"))
        target = fixture_dir(root, version) / record.parent.name / record.name
        if target.exists():
            skipped += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        copied += 1
    stdout.write(f"{NAME}: imported {copied} record(s) into {fixture_dir(root, version)}; skipped {skipped}\n")
    return 0


def main(argv, stdin, stderr, root=None, config_path=None, home=None, stdout=None) -> int:
    root = Path(root) if root else workspace_root()
    if len(argv) == 2 and argv[0] == "--import":
        try:
            patterns = load_patterns(Path(config_path) if config_path else default_config_path())
        except PatternLoadError as exc:
            stderr.write(f"{NAME}: {exc}\n")
            return 2
        return import_records(root, argv[1], patterns, stdout or sys.stdout, stderr)
    if len(argv) != 1 or not TRIGGER_RE.match(argv[0]):
        stderr.write(f"{NAME}: usage: payload_probe.py <TriggerName>; nothing recorded\n")
        return 0
    try:
        patterns = load_patterns(Path(config_path) if config_path else default_config_path())
    except PatternLoadError as exc:
        # Without patterns the payload cannot be masked, so it is not written.
        stderr.write(f"{NAME}: {exc}; nothing recorded\n")
        return 0
    data = stdin.read(MAX_INPUT_BYTES + 1)[:MAX_INPUT_BYTES]
    home = home if home is not None else os.environ.get("HOME")
    try:
        write_record(sanitize(data, patterns, root, home), argv[0], root)
    except OSError as exc:
        stderr.write(f"{NAME}: could not write probe record: {exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:], sys.stdin.buffer, sys.stderr, stdout=sys.stdout))
