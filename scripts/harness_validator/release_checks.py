"""Release and documentation checks (agent-harness-platform R16.5, R16.6, R17.1, R17.5).

* VERSION-FORMAT / VERSION-CHANGELOG: ``harness/VERSION`` is a semantic version and has a CHANGELOG entry.
* DOC-LINK: a relative Markdown link in docs/, README.md or a spec points to a file that does not exist.
* RELEASE-GATE: the release-checklist Guidance_Source names every release gate.
"""

from __future__ import annotations

import os
import re

from .report import error

SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?$")
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FENCE = re.compile(r"^\s*(```|~~~)")
GATES = ("CI", "Traceability_Report", "Manual_Check_Records", "CHANGELOG", "harness/VERSION")
CHECKLIST = "harness/guidance/release-checklist.md"


def _read(path):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return None


def check_version(root) -> list:
    root = str(root)
    text = _read(os.path.join(root, "harness", "VERSION"))
    if text is None:
        return []  # a project that does not ship the Harness version has nothing to check
    version = text.strip()
    if not SEMVER.match(version):
        return [error("harness/VERSION", "-", "VERSION-FORMAT", f"{version!r} is not a semantic version (MAJOR.MINOR.PATCH)")]
    changelog = _read(os.path.join(root, "CHANGELOG.md"))
    if changelog is None:
        return [error("CHANGELOG.md", "-", "VERSION-CHANGELOG", "CHANGELOG.md is missing")]
    if not re.search(rf"^## \[{re.escape(version)}\]", changelog, re.M):
        return [error("CHANGELOG.md", "-", "VERSION-CHANGELOG", f"no '## [{version}]' entry for harness/VERSION")]
    return []


def _markdown_files(root):
    found = [os.path.join(root, "README.md")]
    for base in ("docs", os.path.join(".kiro", "specs")):
        for folder, dirs, files in os.walk(os.path.join(root, base)):
            dirs[:] = sorted(d for d in dirs if d not in ("fixtures", "__pycache__"))
            found += [os.path.join(folder, n) for n in sorted(files) if n.endswith(".md")]
    return [p for p in found if os.path.isfile(p)]


def check_links(root) -> list:
    root = str(root)
    findings = []
    for path in _markdown_files(root):
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        if rel.startswith("docs/verification/") and rel.count("/") >= 4:
            continue  # recorded Manual_Check_Records are evidence, not navigable docs
        fenced = False
        for number, line in enumerate((_read(path) or "").splitlines(), 1):
            if FENCE.match(line):
                fenced = not fenced
            if fenced:
                continue
            for target in LINK.findall(line):
                if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith(("#", "<")):
                    continue
                resolved = os.path.normpath(os.path.join(os.path.dirname(path), target.split("#", 1)[0]))
                if not os.path.exists(resolved):
                    findings.append(error(rel, f"line {number}", "DOC-LINK", f"relative link {target} points to a file that does not exist"))
    return findings


def check_release_gates(root) -> list:
    text = _read(os.path.join(str(root), CHECKLIST))
    if text is None:
        return []
    return [error(CHECKLIST, "-", "RELEASE-GATE", f"release checklist does not name the gate '{gate}'")
            for gate in GATES if gate not in text]


def check(root) -> list:
    return check_version(root) + check_links(root) + check_release_gates(root)
