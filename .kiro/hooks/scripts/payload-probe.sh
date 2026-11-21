#!/bin/sh
# Example hook (disabled): records the masked hook payload for test fixtures.
# Usage: payload-probe.sh <TriggerName>. Always exits 0 and prints nothing.
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 0
command -v python3 >/dev/null 2>&1 || exit 0
python3 -I "$dir/lib/payload_probe.py" "$@" >/dev/null
exit 0
