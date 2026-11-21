#!/bin/sh
# Runs the Hypothesis property tests in tests/property.
# Uses uv or a local virtualenv in .venv, installing the pinned dev dependency
# when needed. Set HARNESS_OFFLINE=1 to require an already-installed Hypothesis.
# Set HYPOTHESIS_PROFILE=ci for 300 examples per test.
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 2
root=$(CDPATH='' cd -- "$dir/.." && pwd) || exit 2
cd "$root" || exit 2
run='import sys, unittest; sys.path.insert(0, "."); s = unittest.TestLoader().discover("tests/property", top_level_dir="."); r = unittest.TextTestRunner(verbosity=1).run(s); sys.exit(0 if r.wasSuccessful() else 1)'
if [ "${HARNESS_OFFLINE:-0}" = 1 ]; then
  if [ -x .venv/bin/python ]; then
    property_python=.venv/bin/python
  else
    property_python=$(command -v python3) || {
      echo "test-properties: python3 not found" >&2
      exit 2
    }
  fi
  if ! "$property_python" -c 'import hypothesis' >/dev/null 2>&1; then
    echo "test-properties: Hypothesis is not installed; install requirements-dev.txt before using offline mode" >&2
    exit 2
  fi
  exec "$property_python" -c "$run"
fi
if command -v uv >/dev/null 2>&1; then
  exec uv run --no-project --with-requirements requirements-dev.txt python -c "$run"
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "test-properties: python3 not found" >&2
  exit 2
fi
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv || exit 2
  .venv/bin/python -m pip install -q -r requirements-dev.txt || exit 2
fi
exec .venv/bin/python -c "$run"
