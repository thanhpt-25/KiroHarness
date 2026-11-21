"""Traceability: criteria, tasks, Validates_Tags and Manual_Check_Records (agent-harness-platform R14.1, R14.2, R14.6).

``analyze`` is pure so Property 42 can run it over generated inputs. ``scan_*``
read the repository. Rules: TRACE-UNCOVERED, TRACE-DANGLING (errors),
TRACE-BACKLOG (error for unknown ids, warning for ids that gained coverage).
"""

from __future__ import annotations

import json
import os
import re

from . import frontmatter, spec_lint
from .report import error, warning

TAG_LINE = re.compile(r"Validates:\s*(.+)")
TAG_ID = re.compile(r"([a-z0-9][a-z0-9-]*)/R(\d+)\.(\d+)")
REQUIRED_SPECS = ("agent-harness-platform", "kiro-agent-harness-template")
BACKLOG = "docs/verification/backlog.txt"


def _read(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return None


def scan_criteria(root) -> dict:
    """``{spec: {"n.m": line}}`` for every spec directory with a requirements.md."""
    specs_dir = os.path.join(root, ".kiro", "specs")
    found = {}
    for name in sorted(os.listdir(specs_dir)) if os.path.isdir(specs_dir) else []:
        text = _read(os.path.join(specs_dir, name, "requirements.md"))
        if text is None:
            continue
        _sections, reqs = spec_lint.parse_requirements(text)
        found[name] = {f"{r.number}.{m}": line for r in reqs for m, _t, line in r.criteria}
    return found


def scan_task_refs(root, specs) -> dict:
    """``{spec: {"n.m": line}}`` of criteria referenced by tasks."""
    out = {}
    for name in specs:
        text = _read(os.path.join(root, ".kiro", "specs", name, "tasks.md"))
        out[name] = spec_lint.referenced_ids(text) if text else {}
    return out


def scan_tags(root) -> list:
    """``[(relative path, line, spec, "n.m", test or None)]`` from ``# Validates:`` lines in tests/."""
    tags = []
    tests_dir = os.path.join(root, "tests")
    for folder, dirs, files in os.walk(tests_dir):
        dirs[:] = sorted(d for d in dirs if d not in ("__pycache__", "fixtures"))
        for name in sorted(files):
            if not name.endswith(".py"):
                continue
            path = os.path.join(folder, name)
            text = _read(path)
            if text is None:
                continue
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            lines = text.splitlines()
            for index, line in enumerate(lines):
                match = TAG_LINE.search(line)
                if not match or ("#" not in line and '"""' not in "\n".join(lines[max(0, index - 6): index + 1]) and "Validates" not in line):
                    continue
                test = None
                if line.startswith((" ", "\t")):  # inside a class: tied to the next test method
                    for later in lines[index + 1: index + 8]:
                        found = re.match(r"\s+def (test_\w+)", later)
                        if found:
                            test = found.group(1)
                            break
                for spec, n, m in TAG_ID.findall(match.group(1)):
                    tags.append((rel, index + 1, spec, f"{n}.{m}", test))
    return tags


def scan_records(root) -> list:
    """``[(path, spec, "n.m")]`` from ``criteria:`` in Manual_Check_Record front matter."""
    records = []
    base = os.path.join(root, "docs", "verification")
    for folder, _dirs, files in os.walk(base):
        for name in sorted(files):
            if not name.endswith(".md"):
                continue
            path = os.path.join(folder, name)
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            if rel.count("/") < 4:  # docs/verification/<agent>/<version>/<check>.md
                continue
            split = frontmatter.split_front_matter(_read(path) or "")
            if split is None:
                continue
            try:
                data = frontmatter.parse_front_matter(split[0])
            except frontmatter.FrontMatterError:
                continue
            for item in data.get("criteria") or []:
                for spec, n, m in TAG_ID.findall(str(item)):
                    records.append((rel, spec, f"{n}.{m}"))
    return records


def read_backlog(root) -> list:
    text = _read(os.path.join(root, BACKLOG)) or ""
    return [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith("#")]


def analyze(criteria: dict, tags, records):
    """Return ``(uncovered, dangling)``.

    ``criteria`` is ``{spec: collection of "n.m"}``; ``tags`` are ``(path, line, spec, id, ...)``;
    ``records`` are ``(path, spec, id)``. ``uncovered`` lists ``"spec/Rn.m"`` for each
    criterion with neither a tag nor a record. ``dangling`` lists the tags (and records) whose
    criterion does not exist.
    """
    known = {f"{spec}/R{cid}" for spec, ids in criteria.items() for cid in ids}
    covered = {f"{t[2]}/R{t[3]}" for t in tags} | {f"{r[1]}/R{r[2]}" for r in records}
    uncovered = sorted(known - covered)
    dangling = sorted({(t[0], t[1], f"{t[2]}/R{t[3]}") for t in tags if f"{t[2]}/R{t[3]}" not in known}
                      | {(r[0], 0, f"{r[1]}/R{r[2]}") for r in records if f"{r[1]}/R{r[2]}" not in known})
    return uncovered, dangling


def required_criteria(criteria: dict) -> dict:
    return {spec: ids for spec, ids in criteria.items() if spec in REQUIRED_SPECS}


def check(root) -> list:
    criteria = scan_criteria(root)
    tags, records = scan_tags(root), scan_records(root)
    uncovered, dangling = analyze(required_criteria(criteria), tags, records)
    _u, dangling = analyze(criteria, tags, records)  # tags may not name a missing criterion in any spec
    backlog = set(read_backlog(root))
    known = {f"{s}/R{c}" for s, ids in criteria.items() for c in ids}
    findings = []
    for cid in uncovered:
        if cid not in backlog:
            findings.append(error(f".kiro/specs/{cid.split('/')[0]}/requirements.md", cid, "TRACE-UNCOVERED",
                                  f"criterion {cid} has no test with a Validates tag and no Manual_Check_Record"))
    for path, line, cid in dangling:
        findings.append(error(path, f"line {line}" if line else "criteria", "TRACE-DANGLING", f"Validates tag names {cid}, which does not exist"))
    for cid in sorted(backlog):
        if cid not in known:
            findings.append(error(BACKLOG, cid, "TRACE-BACKLOG", f"backlog entry {cid} names no criterion"))
        elif cid not in uncovered:
            findings.append(warning(BACKLOG, cid, "TRACE-BACKLOG", f"{cid} is covered now; remove it from the backlog"))
    return findings


def build_report(root, results=None) -> dict:
    """The Traceability_Report as a dict (agent-harness-platform R14.1, R14.6)."""
    criteria = scan_criteria(root)
    tasks = scan_task_refs(root, criteria)
    tags, records = scan_tags(root), scan_records(root)
    statuses = results or {}
    report = {}
    for spec, ids in criteria.items():
        for cid in ids:
            key = f"{spec}/R{cid}"
            tests = []
            for path, line, t_spec, t_id, test in tags:
                if (t_spec, t_id) == (spec, cid):
                    module = path[:-3].replace("/", ".")
                    status = _status(statuses, module, test)
                    tests.append({"file": path, "line": line, "test": test, "status": status})
            report[key] = {"tasks": sorted(tasks[spec].keys() & {cid}) and [tasks[spec][cid]] or [],
                           "tests": tests, "records": sorted(r[0] for r in records if (r[1], r[2]) == (spec, cid))}
    uncovered, dangling = analyze(required_criteria(criteria), tags, records)
    skipped = sorted({(path, test, s[1]) for path, _l, _sp, _id, test in tags
                      for tid, s in statuses.items() if tid.startswith(path[:-3].replace("/", ".")) and (test is None or tid.endswith("." + test)) and s[0] == "skipped"})
    return {"criteria": report, "uncovered": uncovered, "dangling": [list(d) for d in dangling],
            "skipped": [{"test": t, "file": p, "reason": r, "criteria": sorted(f"{sp}/R{i}" for pp, _l, sp, i, tt in tags if pp == p and (tt is None or t is None or tt == t))} for p, t, r in skipped]}


def _status(statuses, module, test):
    matches = [s[0] for tid, s in statuses.items() if tid.startswith(module + ".") and (test is None or tid.endswith("." + test))]
    if not matches:
        return "unknown"
    if "failed" in matches:
        return "failed"
    return "skipped" if all(m == "skipped" for m in matches) else "passed"


def load_results(root):
    text = _read(os.path.join(root, "build", "test-results.json"))
    if not text:
        return {}
    try:
        return {k: tuple(v) for k, v in json.loads(text).items()}
    except (ValueError, TypeError):
        return {}


def markdown(report: dict) -> str:
    total = len(report["criteria"])
    lines = ["# Traceability report", "", f"Criteria: {total}; uncovered (required specs): {len(report['uncovered'])}; dangling tags: {len(report['dangling'])}; skipped tests: {len(report['skipped'])}", ""]
    if report["uncovered"]:
        lines += ["## Uncovered", ""] + [f"- {c}" for c in report["uncovered"]] + [""]
    if report["dangling"]:
        lines += ["## Dangling tags", ""] + [f"- {p}:{l} names {c}" for p, l, c in report["dangling"]] + [""]
    if report["skipped"]:
        lines += ["## Skipped tests", ""] + [f"- {s['test'] or s['file']}: {s['reason']} (would validate {', '.join(s['criteria'])})" for s in report["skipped"]] + [""]
    return "\n".join(lines)
