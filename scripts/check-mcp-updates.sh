#!/bin/sh
# Compares the uvx package pins in .kiro/settings/mcp.json with the latest
# releases on PyPI. Needs network access. Changes no files. Never run by hooks
# or by scripts/validate.sh.
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 2
config="$dir/../.kiro/settings/mcp.json"
if ! command -v python3 >/dev/null 2>&1; then
  echo "check-mcp-updates: python3 not found" >&2
  exit 2
fi
exec python3 -I - "$config" <<'EOF'
import json, re, sys, urllib.error, urllib.parse, urllib.request

PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)@([0-9]+\.[0-9]+\.[0-9]+)$")
path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as handle:
        servers = json.load(handle).get("mcpServers", {})
except (OSError, ValueError) as exc:
    sys.exit(f"check-mcp-updates: could not read {path}: {exc}")

rows, status = [], 0
for server, entry in sorted(servers.items()):
    args = entry.get("args") or []
    spec = None
    for index, arg in enumerate(args):
        if arg == "--from" and index + 1 < len(args):
            spec = args[index + 1]
            break
    if spec is None and args:
        spec = args[0]
    match = PIN.match(spec or "")
    if entry.get("command") != "uvx" or not match:
        rows.append((server, spec or "-", "-", "-", "not a pinned uvx package"))
        continue
    package, pinned = match.groups()
    url = f"https://pypi.org/pypi/{urllib.parse.quote(package)}/json"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            latest = json.load(response)["info"]["version"]
    except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
        rows.append((server, package, pinned, "?", f"lookup failed: {exc}"))
        status = 1
        continue
    note = "up to date" if latest == pinned else "update available"
    rows.append((server, package, pinned, latest, note))

header = ("server", "package", "pinned", "latest", "status")
widths = [max(len(str(r[i])) for r in rows + [header]) for i in range(5)]
for row in [header] + rows:
    print("  ".join(str(value).ljust(width) for value, width in zip(row, widths)).rstrip())
sys.exit(status)
EOF
