"""``scripts/harness`` command line. Exit codes: 0 ok, 1 findings, 2 usage or internal error."""

from __future__ import annotations

import argparse
import json
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
    inv = sub.add_parser("mcp-inventory", help="write or compare tool inventories of the pinned MCP servers (starts the servers; needs uvx and network)")
    inv.add_argument("--check", action="store_true", help="compare live tools with harness/mcp/*.tools.json; exit 1 on any difference")
    inv.add_argument("--server", action="append", help="limit to this server (repeatable)")
    log = sub.add_parser("log", help="show the Decision_Log")
    log.add_argument("--summary", action="store_true", required=True, help="count each Decision per guard and the ten most frequent matched entries")
    new = sub.add_parser("new-spec", help="create .kiro/specs/<name>/ with a skeleton that passes the Spec_Linter")
    new.add_argument("name", help="spec name: lowercase letters, digits and hyphens")
    trace = sub.add_parser("trace", help="print the Traceability_Report and write build/traceability.json")
    trace.add_argument("--json", action="store_true", help="print the JSON report instead of Markdown")
    return parser


def main(argv, out=None, err=None) -> int:
    out, err = out or sys.stdout, err or sys.stderr
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    if args.command == "trace":
        from harness_validator import trace_check

        report = trace_check.build_report(args.root, trace_check.load_results(args.root))
        target = os.path.join(args.root, "build", "traceability.json")
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")
        out.write(json.dumps(report, indent=2, sort_keys=True) + "\n" if args.json else trace_check.markdown(report))
        return 1 if report["uncovered"] or report["dangling"] else 0
    if args.command == "new-spec":
        from . import specs

        code, message = specs.create(args.root, args.name)
        (out if code == 0 else err).write(message + "\n")
        return code
    if args.command == "log":
        sys.path.insert(0, os.path.join(args.root, "harness", "core"))
        import decision_log

        out.write(decision_log.summarize(decision_log.read_records(args.root)))
        return 0
    try:
        plan = plan_mod.build_plan(args.root)
    except ManifestError as exc:
        for problem in exc.problems:
            err.write(f"harness: {problem}\n")
        return 2
    except Exception as exc:  # an internal error must not look like drift
        err.write(f"harness: internal error: {exc.__class__.__name__}: {exc}\n")
        return 2
    if args.command == "mcp-inventory":
        from . import mcp_inventory
        from harness_validator import manifest as manifest_mod

        servers = manifest_mod.load(args.root)["mcp"]
        return mcp_inventory.run(args.root, servers, args.server, args.check, out)
    for warning in plan.warnings:
        err.write(f"warning: {warning}\n")
    if args.command == "sync":
        if args.check:
            return sync_mod.check(args.root, plan, out)
        return sync_mod.sync(args.root, plan, args.force, out, err)
    return 2
