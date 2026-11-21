#!/bin/sh
# Mutation testing of the guard modules (agent-harness-platform R14.4). Dev-only and slow; run weekly by
# .github/workflows/nightly.yml. Needs `python3 -m pip install -r requirements-mutation.txt -r requirements-dev.txt`.
# Fails when the mutation score of any guard module is below HARNESS_MUTATION_MIN (default 85 percent)
# and lists the surviving mutants. Usage: scripts/mutation.sh [module ...]
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 2
cd "$dir/.." || exit 2
python3 -m mutmut --help >/dev/null 2>&1 || {
  echo "mutation: install requirements-mutation.txt first" >&2
  exit 2
}
min=${HARNESS_MUTATION_MIN:-85}
modules=${*:-"destructive_guard risky_guard prompt_scan protected_paths guards"}
status=0
for module in $modules; do
  case $module in
    destructive_guard) tests="tests.hooks.test_destructive_guard tests.property.test_p44_policy_roundtrip" ;;
    risky_guard) tests="tests.hooks.test_risky_guard tests.core.test_event_model_and_adapters" ;;
    prompt_scan) tests="tests.hooks.test_kiro_fixtures tests.property.test_p19_prompt_scan" ;;
    protected_paths) tests="tests.core.test_protected_paths tests.property.test_p38_protected_paths" ;;
    guards) tests="tests.core.test_guard_cli tests.property.test_p32_guard_combination" ;;
    *) echo "mutation: unknown module $module" >&2; exit 2 ;;
  esac
  rm -rf .mutmut-cache
  python3 -m mutmut run --paths-to-mutate "harness/core/$module.py" \
    --runner "python3 -m unittest $tests" --tests-dir tests --no-progress >/dev/null 2>&1
  mkdir -p build
  python3 -m mutmut junitxml > "build/mutation-$module.xml"
  python3 - "$module" "$min" <<'PY' || status=1
import sys, xml.etree.ElementTree as ET
name, minimum = sys.argv[1], float(sys.argv[2])
suite = ET.parse(f"build/mutation-{name}.xml").getroot()
suite = suite if suite.tag == "testsuite" else suite.find("testsuite")
total = int(suite.get("tests"))
survived = int(suite.get("failures"))
score = 100.0 * (total - survived) / total if total else 100.0
print(f"mutation: {name}: {total - survived}/{total} killed, score {score:.1f}% (need {minimum:g})")
for case in suite.iter("testcase"):
    if case.find("failure") is not None:
        print(f"  survivor: {case.get('name')}")
sys.exit(0 if score >= minimum else 1)
PY
done
exit $status
