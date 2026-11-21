"""Helpers: a small repository root holding only the Generator's sources."""

import copy
import json
import shutil
import tempfile
from pathlib import Path

from tests._support import ROOT, SCRIPTS  # noqa: F401  (puts scripts/ on sys.path)

from harness_cli import plan as plan_mod
from harness_cli import sync as sync_mod
from harness_cli.main import main

MANIFEST = json.loads((ROOT / "harness/manifest.json").read_text(encoding="utf-8"))


class SourceRoot:
    """Context manager: temp root with the shipped Manifest, schema, guidance and Kiro hook sources."""

    def __init__(self, manifest=None):
        self.manifest = copy.deepcopy(manifest or MANIFEST)

    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory()
        root = Path(self._tmp.name)
        (root / "harness").mkdir()
        shutil.copy(ROOT / "harness/manifest.schema.json", root / "harness/manifest.schema.json")
        shutil.copytree(ROOT / "harness/guidance", root / "harness/guidance")
        shutil.copytree(ROOT / "harness/kiro", root / "harness/kiro")
        self.write_manifest(root, self.manifest)
        return root

    @staticmethod
    def write_manifest(root, manifest) -> None:
        (root / "harness/manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    def __exit__(self, *exc):
        self._tmp.cleanup()
        return False


def with_agents(**enabled):
    manifest = copy.deepcopy(MANIFEST)
    for agent, value in enabled.items():
        manifest["agents"][agent.replace("_", "-")]["enabled"] = value
    return manifest


def run_cli(root, *args):
    """Run ``harness`` in-process. Return ``(exit code, stdout, stderr)``."""
    import io

    out, err = io.StringIO(), io.StringIO()
    code = main(["--root", str(root), *args], out, err)
    return code, out.getvalue(), err.getvalue()


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(Path(root).rglob("*")) if p.is_file()}
