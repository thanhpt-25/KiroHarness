#!/bin/sh
# Coverage gate (agent-harness-platform R14.3): runs the unit and property tests under a pinned,
# dev-only coverage tool, including the sh-wrapped python3 subprocesses, and fails when line
# coverage is below 90 percent or branch coverage is below 80 percent for
# scripts/harness_validator, scripts/harness_cli and harness/core.
# Needs `python3 -m pip install -r requirements-dev.txt` first. Override with
# HARNESS_COVERAGE_LINES / HARNESS_COVERAGE_BRANCHES (percent).
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 2
cd "$dir/.." || exit 2
python3 -c 'import coverage, hypothesis' 2>/dev/null || {
  echo "coverage: install requirements-dev.txt first (coverage and hypothesis)" >&2
  exit 2
}
rm -rf build/.coverage* build/coverage.json
python3 -m coverage run -m unittest discover -s tests -t . || exit 1
python3 -m coverage combine -q || exit 2
python3 -m coverage report
python3 -m coverage json -q -o build/coverage.json || exit 2
python3 - <<'PY'
import json, os, sys
t = json.load(open("build/coverage.json"))["totals"]
lines = 100.0 * t["covered_lines"] / t["num_statements"]
branches = 100.0 * t["covered_branches"] / t["num_branches"]
want_l = float(os.environ.get("HARNESS_COVERAGE_LINES", "90"))
want_b = float(os.environ.get("HARNESS_COVERAGE_BRANCHES", "80"))
print(f"coverage: lines {lines:.1f}% (need {want_l:g}), branches {branches:.1f}% (need {want_b:g})")
sys.exit(0 if lines >= want_l and branches >= want_b else 1)
PY
