"""Spec_Linter: structure, EARS and reference checks for ``.kiro/specs/<name>/`` (agent-harness-platform R13.1 to R13.4).

Rules: SPEC-FILES, SPEC-REQ, SPEC-STORY, SPEC-EARS, SPEC-DESIGN, SPEC-TASKREF (error), SPEC-UNREF (warning).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .report import error, warning

EARS_START = re.compile(r"^(THE|WHEN|WHILE|IF|WHERE)\b")
STORY = re.compile(r"\*\*User Story:\*\*\s*As (?:an?|the) .+?,?\s+I want .+?,?\s+so that\b", re.S)
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
REQUIREMENT = re.compile(r"^###\s+Requirement\s+(\d+)\s*:")
NUMBERED = re.compile(r"^(\d+)\.\s+(.*)$")
TASK_REFS = re.compile(r"_Requirements:\s*([^_\n]+)_|Validates:\s*Requirements?\s+([0-9., ]+)")
CRITERION_ID = re.compile(r"\b(\d+)\.(\d+)\b")
DESIGN_SECTIONS = ("Overview", "Architecture", "Components and Interfaces", "Data Models", "Error Handling", "Testing Strategy")


def is_ears(text: str) -> bool:
    """True when the criterion starts with one of the EARS keyword patterns."""
    return bool(EARS_START.match(text.strip()))


@dataclass
class Requirement:
    number: int
    line: int
    story_ok: bool = False
    criteria: list = field(default_factory=list)  # (m, text, line)


def parse_requirements(text: str):
    """Return ``(section titles, [Requirement])``."""
    lines = text.splitlines()
    sections, reqs, current, in_criteria = set(), [], None, False
    index = 0
    while index < len(lines):
        line = lines[index]
        heading = HEADING.match(line)
        if heading:
            level, title = len(heading.group(1)), heading.group(2)
            if level <= 2:
                sections.add(title)
            match = REQUIREMENT.match(line)
            if match:
                current = Requirement(int(match.group(1)), index + 1)
                reqs.append(current)
                in_criteria = False
            elif current is not None and title.lower().startswith("acceptance criteria"):
                in_criteria = True
            elif current is not None:
                in_criteria = False
        elif current is not None and "**User Story:**" in line:
            block = [line]
            probe = index + 1
            while probe < len(lines) and lines[probe].strip():
                block.append(lines[probe])
                probe += 1
            current.story_ok = bool(STORY.search(" ".join(b.strip() for b in block)))
        elif current is not None and in_criteria:
            numbered = NUMBERED.match(line)
            if numbered:
                current.criteria.append([int(numbered.group(1)), numbered.group(2), index + 1])
            elif current.criteria and line.strip():
                current.criteria[-1][1] += " " + line.strip()
        index += 1
    return sections, reqs


def referenced_ids(tasks_text: str) -> dict:
    """``{"n.m": first line}`` of every criterion a task names."""
    found: dict = {}
    for number, line in enumerate(tasks_text.splitlines(), start=1):
        for match in TASK_REFS.finditer(line):
            for item in CRITERION_ID.finditer(match.group(1) or match.group(2) or ""):
                found.setdefault(f"{item.group(1)}.{item.group(2)}", number)
    return found


def design_headings(text: str) -> set:
    return {m.group(2).strip().lower() for m in (HEADING.match(l) for l in text.splitlines()) if m}


def check_spec(name: str, files: dict) -> list:
    """``files`` maps requirements.md, design.md, tasks.md to text (None when missing)."""
    base = f".kiro/specs/{name}"
    findings = []
    for required in ("requirements.md", "design.md", "tasks.md"):
        if files.get(required) is None:
            findings.append(error(f"{base}/{required}", "-", "SPEC-FILES", f"spec {name} is missing {required}"))
    requirements = files.get("requirements.md")
    known: dict = {}
    if requirements is not None:
        path = f"{base}/requirements.md"
        sections, reqs = parse_requirements(requirements)
        for needed in ("Introduction", "Glossary"):
            if needed not in sections:
                findings.append(error(path, "-", "SPEC-REQ", f"requirements.md has no {needed} section"))
        for req in reqs:
            if not req.story_ok:
                findings.append(error(path, f"line {req.line}", "SPEC-STORY", f'Requirement {req.number} lacks a user story in the form "As a ..., I want ..., so that ..."'))
            if not req.criteria:
                findings.append(error(path, f"line {req.line}", "SPEC-REQ", f"Requirement {req.number} has no acceptance criteria"))
            for m, text, line in req.criteria:
                known[f"{req.number}.{m}"] = line
                if not is_ears(text):
                    findings.append(error(path, f"line {line}", "SPEC-EARS", f"criterion {req.number}.{m} does not start with THE, WHEN, WHILE, IF or WHERE"))
    design = files.get("design.md")
    if design is not None:
        present = design_headings(design)
        for section in DESIGN_SECTIONS:
            if not any(h == section.lower() or h.startswith(section.lower() + " ") or h.startswith(section.lower() + ":") for h in present):
                findings.append(error(f"{base}/design.md", "-", "SPEC-DESIGN", f"design.md has no {section} section"))
    tasks = files.get("tasks.md")
    if tasks is not None and requirements is not None:
        refs = referenced_ids(tasks)
        for ref, line in sorted(refs.items(), key=lambda item: item[1]):
            if ref not in known:
                findings.append(error(f"{base}/tasks.md", f"line {line}", "SPEC-TASKREF", f"task references criterion {ref}, which does not exist in requirements.md"))
        for ref, line in known.items():
            if ref not in refs:
                findings.append(warning(f"{base}/requirements.md", f"line {line}", "SPEC-UNREF", f"criterion {ref} is not referenced by any task"))
    return findings
