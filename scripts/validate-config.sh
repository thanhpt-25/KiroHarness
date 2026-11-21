#!/bin/sh
# Config_Validator: checks steering files, hook files, the MCP config, the
# guard lists, and placeholders. Exit 0 with no errors, 1 with errors,
# 2 on an internal crash. Runs offline with the Python standard library.
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 2
root=$(CDPATH='' cd -- "$dir/.." && pwd) || exit 2
if ! command -v python3 >/dev/null 2>&1; then
  echo "validate-config: python3 not found (Python 3.10 or newer is required)" >&2
  exit 2
fi
# -I ignores PYTHON* variables and the user site directory, so scripts/ is
# added to the module path explicitly.
exec python3 -I -c 'import runpy, sys; sys.path.insert(0, sys.argv.pop(1)); runpy.run_module("harness_validator", run_name="__main__", alter_sys=True)' "$dir" --root "$root" "$@"
