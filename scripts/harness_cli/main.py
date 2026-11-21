"""``scripts/harness`` command line. Exit codes: 0 ok, 1 findings, 2 usage or internal error."""

from __future__ import annotations

import argparse
import os
import sys

from harness_validator.manifest import ManifestError

from . import plan as plan_mod
from . import sync as sync_mod

DEFAULT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="harness", description="Agent harness command line.")
    parser.add_argument("--root", default=DEFAULT_ROOT, help="repository root (default: the checkout containing this script)")
    sub = parser.add_subparsers(dest="command", required=True)
    sync = sub.add_parser("sync", help="render every Generated_File from the Manifest and sources")
    sync.add_argument("--check", action="store_true", help="write nothing; exit 1 with a diff when files drifted")
    sync.add_argument("--force", action="store_true", help="overwrite files that were edited by hand")
    return parser


def main(argv, out=None, err=None) -> int:
    out, err = out or sys.stdout, err or sys.stderr
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        plan = plan_mod.build_plan(args.root)
    except ManifestError as exc:
        for problem in exc.problems:
            err.write(f"harness: {problem}\n")
        return 2
    except Exception as exc:  # an internal error must not look like drift
        err.write(f"harness: internal error: {exc.__class__.__name__}: {exc}\n")
        return 2
    for warning in plan.warnings:
        err.write(f"warning: {warning}\n")
    if args.command == "sync":
        if args.check:
            return sync_mod.check(args.root, plan, out)
        return sync_mod.sync(args.root, plan, args.force, out, err)
    return 2
