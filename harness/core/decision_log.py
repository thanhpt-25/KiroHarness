"""Decision_Log: append-only JSON Lines record of guard Decisions (agent-harness-platform R12.1 to R12.4).

One ``write`` call per record, under 4 KB, with ``O_APPEND``, so concurrent hooks
do not interleave. Every failure is swallowed into one warning on standard error:
logging can never change a Decision (Requirement 12.3). Summaries are masked
with the same rule as every other output (Requirement 11.4) and truncated.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from masking import mask_secrets  # noqa: E402

LOG_RELATIVE = Path(".harness") / "decisions.jsonl"
MAX_BYTES = 5 * 1024 * 1024
KEEP_ROTATED = 3
SUMMARY_LIMIT = 200
RECORD_LIMIT = 4000
ENV_SWITCH = "HARNESS_DECISION_LOG"


def log_path(root) -> Path:
    return Path(root) / LOG_RELATIVE


def summary_of(event, patterns) -> str:
    """Masked, length-limited text of the command, path or URL (never the prompt)."""
    text = event.command if isinstance(event.command, str) else (event.url if isinstance(event.url, str) else ", ".join(event.paths))
    text = mask_secrets(text or "", patterns)
    return text if len(text) <= SUMMARY_LIMIT else text[: SUMMARY_LIMIT - 3] + "..."


def build_record(event, decision, patterns, now=None) -> dict:
    return {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        "agent": event.agent,
        "trigger": event.trigger,
        "category": event.category,
        "tool": event.tool_id,
        "decision": decision.kind,
        "guard": decision.guard,
        "matched": mask_secrets(decision.matched or "", patterns)[:SUMMARY_LIMIT],
        "summary": summary_of(event, patterns),
    }


def rotate(path: Path) -> None:
    """current -> .1 -> .2 -> .3; the oldest is dropped."""
    for index in range(KEEP_ROTATED, 0, -1):
        source = path if index == 1 else path.with_name(f"{path.name}.{index - 1}")
        target = path.with_name(f"{path.name}.{index}")
        if source.exists():
            os.replace(source, target)


def append(root, records, now=None, max_bytes: int = MAX_BYTES) -> None:
    path = log_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > max_bytes:
        rotate(path)
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        for record in records:
            line = json.dumps(record, ensure_ascii=False)
            if len(line.encode("utf-8")) > RECORD_LIMIT:
                record = dict(record, summary="", matched="")
                line = json.dumps(record, ensure_ascii=False)
            os.write(fd, (line + "\n").encode("utf-8"))
    finally:
        os.close(fd)


def record_decisions(root, event, decisions, patterns, stderr, env=None, now=None) -> None:
    """Log one record per Decision. Never raises."""
    if (env if env is not None else os.environ).get(ENV_SWITCH) == "0" or event is None:
        return
    try:
        append(root, [build_record(event, d, patterns, now) for d in decisions], now)
    except Exception as exc:  # the Decision must not change because logging failed
        try:
            stderr.write(f"decision-log: could not write {log_path(root)}: {exc}\n")
        except Exception:
            pass


def read_records(root) -> list:
    path = log_path(root)
    records = []
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                records.append(json.loads(line))
            except ValueError:
                continue
    return records


def summarize(records) -> str:
    """Counts of each Decision per guard and the ten most frequent matched entries (R12.5)."""
    per_guard: dict = {}
    matched: dict = {}
    for record in records:
        counts = per_guard.setdefault(record.get("guard", "?"), {})
        counts[record.get("decision", "?")] = counts.get(record.get("decision", "?"), 0) + 1
        if record.get("matched"):
            key = (record.get("guard", "?"), record["matched"])
            matched[key] = matched.get(key, 0) + 1
    lines = [f"Decisions: {len(records)}", ""]
    for guard in sorted(per_guard):
        lines.append(f"{guard}: " + ", ".join(f"{kind} {n}" for kind, n in sorted(per_guard[guard].items())))
    lines += ["", "Most frequent matched entries:"]
    top = sorted(matched.items(), key=lambda item: (-item[1], item[0]))[:10]
    lines += [f"  {n:>5}  {guard}: {entry}" for (guard, entry), n in top] or ["  none"]
    return "\n".join(lines) + "\n"
