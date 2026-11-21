#!/bin/sh
# Validation_Command: runs the Config_Validator and every hook script and
# validator test in one invocation. Every test runs even when one fails.
# Exit 0 only when the validator reports zero errors and every test passes.
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 2
root=${HARNESS_VALIDATE_ROOT:-$(CDPATH='' cd -- "$dir/.." && pwd)} || exit 2
test_dirs=${HARNESS_TEST_DIRS:-"tests/hooks tests/validator tests/core tests/generator tests/evals"}
if ! command -v python3 >/dev/null 2>&1; then
  echo "validate: python3 not found (Python 3.10 or newer is required)" >&2
  exit 2
fi

echo "== Config_Validator =="
report=$(sh "$dir/validate-config.sh" --root "$root" 2>&1)
validator_rc=$?
printf '%s\n' "$report"

echo "== Hook script and validator tests =="
cd "$root" || exit 2
# shellcheck disable=SC2086
test_output=$(python3 -I -c 'import sys; sys.path.insert(0, sys.argv.pop(1)); from tests._result import main; sys.exit(main(sys.argv[1:]))' "$root" "$root" $test_dirs 2>&1)
tests_rc=$?
printf '%s\n' "$test_output" | grep -v '^TESTS-SUMMARY '

summary=$(printf '%s\n' "$report" | sed -n 's/^Summary: \([0-9]*\) files\{0,1\} checked, \([0-9]*\) errors\{0,1\}, \([0-9]*\) warnings\{0,1\}$/\1 \2 \3/p' | tail -n 1)
files=${summary%% *}
warnings=${summary##* }
passed=$(printf '%s\n' "$test_output" | sed -n 's/^TESTS-SUMMARY passed=\([0-9]*\) failed=\([0-9]*\)$/\1/p' | tail -n 1)
failed=$(printf '%s\n' "$test_output" | sed -n 's/^TESTS-SUMMARY passed=\([0-9]*\) failed=\([0-9]*\)$/\2/p' | tail -n 1)
[ -n "$files" ] || files="?"
[ -n "$warnings" ] || warnings="?"
[ -n "$passed" ] || passed=0
[ -n "$failed" ] || failed="?"

echo "Validation: $files files checked, $warnings warnings; Tests: $passed passed, $failed failed"
if [ "$validator_rc" -ne 0 ]; then
  echo "validate: FAILED: the Config_Validator exited with code $validator_rc (errors are listed above)"
fi
if [ "$tests_rc" -ne 0 ]; then
  echo "validate: FAILED: $failed test(s) failed (details are listed above)"
fi
if [ "$validator_rc" -eq 0 ] && [ "$tests_rc" -eq 0 ]; then
  exit 0
fi
exit 1
