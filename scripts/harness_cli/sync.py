"""``harness sync``: write, check and protect Generated_Files (agent-harness-platform R6.2 to R6.6)."""

from __future__ import annotations

import difflib
import json
import os

from . import plan as plan_mod


def _read(root, rel):
    try:
        with open(os.path.join(root, rel), encoding="utf-8", newline="") as handle:
            return handle.read()
    except FileNotFoundError:
        return None


def _write(root, rel, text) -> None:
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    os.replace(tmp, path)


def _lock_files(root) -> dict:
    text = _read(root, plan_mod.LOCK_PATH)
    if not text:
        return {}
    try:
        return {p: e["sha256"] for p, e in json.loads(text)["files"].items()}
    except (ValueError, KeyError, TypeError):
        return {}


def analyze(root, plan):
    """Return ``(changes, orphans, hand_edited)``; each is a sorted list of paths."""
    lock = _lock_files(root)
    changes, hand_edited = [], []
    for path, planned in sorted(plan.files.items()):
        disk = _read(root, path)
        if disk is None:
            changes.append(path)
        elif disk != planned.content:
            if lock.get(path) == plan_mod.sha256(disk):
                changes.append(path)  # unedited since the last sync; the sources changed
            else:
                hand_edited.append(path)
    orphans = []
    for path, digest in sorted(lock.items()):
        if path in plan.files:
            continue
        disk = _read(root, path)
        if disk is None:
            continue
        orphans.append(path)
        if plan_mod.sha256(disk) != digest:
            hand_edited.append(path)
    return changes, orphans, sorted(set(hand_edited))


def sync(root, plan, force: bool, out, err) -> int:
    changes, orphans, hand_edited = analyze(root, plan)
    if hand_edited and not force:
        for path in hand_edited:
            err.write(f"sync: {path} was edited by hand; edit its sources or pass --force to overwrite it\n")
        return 1
    for path in sorted(set(changes) | {p for p in hand_edited}):
        if path in plan.files:
            _write(root, path, plan.files[path].content)
            out.write(f"wrote {path}\n")
    for path in orphans:
        os.remove(os.path.join(root, path))
        out.write(f"removed {path}\n")
    lock = plan_mod.lock_text(plan)
    if _read(root, plan_mod.LOCK_PATH) != lock:
        _write(root, plan_mod.LOCK_PATH, lock)
        out.write(f"wrote {plan_mod.LOCK_PATH}\n")
    return 0


def drift(root, plan) -> list:
    """Return ``[(path, unified diff text), ...]`` for every file that differs from the plan."""
    found = []
    for path, planned in sorted(plan.files.items()):
        disk = _read(root, path)
        if disk != planned.content:
            diff = difflib.unified_diff((disk or "").splitlines(True), planned.content.splitlines(True),
                                        f"a/{path}" if disk is not None else "/dev/null", f"b/{path}")
            found.append((path, "".join(diff)))
    lock = plan_mod.lock_text(plan)
    disk_lock = _read(root, plan_mod.LOCK_PATH)
    if disk_lock != lock:
        diff = difflib.unified_diff((disk_lock or "").splitlines(True), lock.splitlines(True), f"a/{plan_mod.LOCK_PATH}", f"b/{plan_mod.LOCK_PATH}")
        found.append((plan_mod.LOCK_PATH, "".join(diff)))
    for path in _lock_files(root):
        if path not in plan.files and _read(root, path) is not None:
            found.append((path, f"{path} is generated for an Agent that is no longer enabled\n"))
    return found


def check(root, plan, out) -> int:
    found = drift(root, plan)
    for path, diff in found:
        out.write(f"drift: {path}\n{diff}")
    return 1 if found else 0
