#!/bin/sh
# Copy masked payloads recorded by the payload-probe example hook from
# .harness/probe/ into tests/fixtures/payloads/kiro/<kiro-version>/.
# Usage: scripts/import-payloads.sh <kiro-version>
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 2
root=$(CDPATH='' cd -- "$dir/.." && pwd) || exit 2
if [ "$#" -ne 1 ]; then
  echo "usage: scripts/import-payloads.sh <kiro-version>" >&2
  exit 2
fi
exec python3 -I "$root/harness/core/payload_probe.py" --import "$1"
