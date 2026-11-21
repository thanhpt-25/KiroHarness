"""``harness init`` and ``harness upgrade`` (agent-harness-platform R17.2, R17.3).

The installed set is every Harness file a project needs: runtime and tooling (Harness-owned, always
replaced on upgrade) and the files a project customizes (Policy_Files, Guidance_Sources, the Manifest,
Kiro hook sources, project commands, validator tunables). Customizable files are compared with
``harness/release.lock.json``, which records the hash each file had when it was installed or last
upgraded. A file the developer edited is never overwritten; a changed upstream version of it is reported
as a conflict with a diff.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import shutil
import subprocess
import sys

RELEASE_LOCK = "harness/release.lock.json"
ROOTS = ("harness", "scripts", ".kiro/hooks", ".githooks")
SINGLE = (".env.example",)
SKIP_NAMES = ("__pycache__", ".DS_Store", "generated.lock.json", "release.lock.json", "mcp")
SKIP_PREFIXES = ("harness/mcp/",)
CUSTOMIZABLE_PREFIXES = ("harness/policy/", "harness/guidance/", "harness/kiro/hooks/")
CUSTOMIZABLE_FILES = ("harness/manifest.json", "scripts/project-commands.env", "scripts/validator-config.json", ".env.example")
AGENTS = ("kiro", "claude-code", "cursor", "copilot")


def digest(path) -> str:
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def is_customizable(rel: str) -> bool:
    return rel in CUSTOMIZABLE_FILES or rel.startswith(CUSTOMIZABLE_PREFIXES)


def install_set(source: str) -> dict:
    """``{relative path: absolute path}`` of every file a project installs from ``source``."""
    found = {}
    for top in ROOTS:
        for folder, dirs, files in os.walk(os.path.join(source, top)):
            dirs[:] = sorted(d for d in dirs if d not in ("__pycache__",))
            for name in sorted(files):
                full = os.path.join(folder, name)
                rel = os.path.relpath(full, source).replace(os.sep, "/")
                if name in SKIP_NAMES or name.endswith(".pyc") or rel.startswith(SKIP_PREFIXES):
                    continue
                found[rel] = full
    for rel in SINGLE:
        if os.path.isfile(os.path.join(source, rel)):
            found[rel] = os.path.join(source, rel)
    return found


def _copy(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)


def _write_release_lock(source, target, files):
    version = _read_version(source)
    lock = {"schema": 1, "harness_version": version, "files": {r: digest(f) for r, f in sorted(files.items()) if is_customizable(r)}}
    path = os.path.join(target, RELEASE_LOCK)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(lock, handle, indent=2, sort_keys=True)
        handle.write("\n")


def _read_version(root) -> str:
    try:
        with open(os.path.join(root, "harness", "VERSION"), encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return "unknown"


def _sh(target, *args):
    return subprocess.run(list(args), cwd=target, capture_output=True, text=True)


def init(source, target, agents, force, out, err, validate=True) -> int:
    unknown = [a for a in agents if a not in AGENTS]
    if unknown or not agents:
        err.write(f"init: choose at least one Agent from {', '.join(AGENTS)}; unknown: {', '.join(unknown) or 'none given'}\n")
        return 2
    files = install_set(source)
    existing = sorted(r for r in files if os.path.exists(os.path.join(target, r)))
    if existing and not force:
        err.write("init: refusing to overwrite existing files (pass --force to replace them):\n")
        for rel in existing[:20]:
            err.write(f"  {rel}\n")
        return 1
    for rel, src in files.items():
        _copy(src, os.path.join(target, rel))
    manifest_path = os.path.join(target, "harness", "manifest.json")
    with open(manifest_path, encoding="utf-8") as handle:
        manifest = json.load(handle)
    manifest["agents"] = {name: {**manifest["agents"].get(name, {}), "enabled": name in agents} for name in AGENTS}
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2)
        handle.write("\n")
    _write_release_lock(source, target, {**files, "harness/manifest.json": manifest_path})
    _write_stubs(target, _read_version(source))
    code = _run_cli(target, ["sync"], out, err)
    if code != 0:
        err.write("init: the Generator failed; see the messages above\n")
        return 1
    if validate:
        result = _sh(target, "sh", os.path.join(target, "scripts", "validate-config.sh"), "--root", target)
        out.write(result.stdout)
        if result.returncode != 0:
            err.write("init: the Validation_Command reported errors; see the output above\n")
            return 1
    out.write(f"init: installed Harness {_read_version(source)} into {target} for {', '.join(agents)}\n")
    return 0


def _write_stubs(target, version) -> None:
    """Create README.md (placeholder inventory) and CHANGELOG.md when the project has none."""
    from harness_validator import placeholders

    changelog = os.path.join(target, "CHANGELOG.md")
    if not os.path.exists(changelog):
        with open(changelog, "w", encoding="utf-8") as handle:
            handle.write(f"# Changelog\n\n## [Unreleased]\n\n## [{version}]\n\n- Installed the Harness {version} with `scripts/harness init`.\n")
    readme = os.path.join(target, "README.md")
    if os.path.exists(readme):
        return
    found = {}
    for folder, dirs, files in os.walk(target):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__", ".venv", "node_modules")]
        for name in files:
            full = os.path.join(folder, name)
            rel = os.path.relpath(full, target).replace(os.sep, "/")
            try:
                with open(full, encoding="utf-8") as handle:
                    names = placeholders.find_placeholders(handle.read())
            except (OSError, UnicodeDecodeError):
                continue
            for item in names:
                found.setdefault(item, []).append(rel)
    lines = ["# Project", "", "## Placeholders", "",
             "Replace these project-specific placeholders before relying on the steering guidance.", ""]
    for item in sorted(found):
        lines.append(f"- `{{{{{item}}}}}` — {', '.join(sorted(found[item]))} — replace with your project's value.")
    with open(readme, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")


def _run_cli(target, argv, out, err) -> int:
    from . import main as main_mod

    return main_mod.main(["--root", target, *argv], out, err)


def plan_upgrade(source, target):
    """Return ``(add, update, keep, conflicts)`` lists of relative paths."""
    files = install_set(source)
    base = {}
    try:
        with open(os.path.join(target, RELEASE_LOCK), encoding="utf-8") as handle:
            base = json.load(handle).get("files", {})
    except (OSError, ValueError):
        pass
    add, update, keep, conflicts = [], [], [], []
    for rel, src in sorted(files.items()):
        dst = os.path.join(target, rel)
        if not os.path.exists(dst):
            add.append(rel)
        elif digest(dst) == digest(src):
            continue
        elif rel == "harness/manifest.json":
            keep.append(rel)  # records this project's Agent selection; never replaced
        elif not is_customizable(rel):
            update.append(rel)
        elif base.get(rel) == digest(dst):  # unedited since install: safe to take the new version
            update.append(rel)
        elif base.get(rel) == digest(src):  # edited here, unchanged upstream: keep the edit
            keep.append(rel)
        else:  # edited here and changed upstream (or no base to tell)
            conflicts.append(rel)
    return add, update, keep, conflicts


def upgrade(source, target, out, err) -> int:
    if not os.path.isfile(os.path.join(target, "harness", "manifest.json")):
        err.write("upgrade: the target has no harness/manifest.json; run `harness init` first\n")
        return 2
    add, update, keep, conflicts = plan_upgrade(source, target)
    files = install_set(source)
    for rel in add + update:
        _copy(files[rel], os.path.join(target, rel))
    for rel in conflicts:
        with open(os.path.join(target, rel), encoding="utf-8", errors="replace") as mine, open(files[rel], encoding="utf-8", errors="replace") as theirs:
            diff = difflib.unified_diff(mine.read().splitlines(True), theirs.read().splitlines(True),
                                        f"{rel} (yours)", f"{rel} ({_read_version(source)})")
        out.write(f"conflict: {rel} was edited here and changed upstream; left unchanged\n{''.join(diff)}")
    if not conflicts:
        _write_release_lock(source, target, {**files, "harness/manifest.json": os.path.join(target, "harness", "manifest.json")})
    out.write(f"upgrade: {len(add)} added, {len(update)} updated, {len(keep)} kept (edited here), {len(conflicts)} conflict(s)\n")
    if conflicts:
        out.write("upgrade: resolve the conflicts above by hand, then run `harness upgrade` again to record the new version\n")
        return 1
    code = _run_cli(target, ["sync"], out, err)
    return 0 if code == 0 else 1
