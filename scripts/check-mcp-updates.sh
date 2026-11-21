#!/bin/sh
# Compares the uvx package pins in .kiro/settings/mcp.json with the latest
# releases on PyPI and lists known security advisories (OSV) for each pinned
# package. Needs network access. Changes no files. Never run by hooks or by
# scripts/validate.sh. HARNESS_PYPI_URL and HARNESS_OSV_URL override the
# endpoints (used by tests). Exit 1 when a lookup failed or an advisory exists.
dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd) || exit 2
config="$dir/../.kiro/settings/mcp.json"
if ! command -v python3 >/dev/null 2>&1; then
  echo "check-mcp-updates: python3 not found" >&2
  exit 2
fi
exec python3 -I - "$config" <<'EOF'
import json, os, re, sys, urllib.error, urllib.parse, urllib.request

PYPI = os.environ.get("HARNESS_PYPI_URL", "https://pypi.org/pypi").rstrip("/")
OSV = os.environ.get("HARNESS_OSV_URL", "https://api.osv.dev/v1/query")

PIN = re.compile(r"^([A-Za-z0-9][A-Za-z0-9._-]*)@([0-9]+\.[0-9]+\.[0-9]+)$")
path = sys.argv[1]
try:
    with open(path, encoding="utf-8") as handle:
        servers = json.load(handle).get("mcpServers", {})
except (OSError, ValueError) as exc:
    sys.exit(f"check-mcp-updates: could not read {path}: {exc}")

rows, advisories, status = [], [], 0
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
    url = f"{PYPI}/{urllib.parse.quote(package)}/json"
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            latest = json.load(response)["info"]["version"]
    except (urllib.error.URLError, OSError, ValueError, KeyError) as exc:
        rows.append((server, package, pinned, "?", f"lookup failed: {exc}"))
        status = 1
        continue
    note = "up to date" if latest == pinned else "update available"
    try:
        request = urllib.request.Request(OSV, data=json.dumps({"package": {"name": package, "ecosystem": "PyPI"}, "version": pinned}).encode(),
                                         headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=15) as response:
            vulns = json.load(response).get("vulns", [])
        if vulns:
            advisories.append((server, package, pinned, [v.get("id", "?") + (": " + v["summary"] if v.get("summary") else "") for v in vulns]))
            note += f", {len(vulns)} advisory(ies)"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        note += f", advisory lookup failed: {exc}"
        status = 1
    rows.append((server, package, pinned, latest, note))

header = ("server", "package", "pinned", "latest", "status")
widths = [max(len(str(r[i])) for r in rows + [header]) for i in range(5)]
for row in [header] + rows:
    print("  ".join(str(value).ljust(width) for value, width in zip(row, widths)).rstrip())
for server, package, pinned, items in advisories:
    print(f"\nadvisories for {server} ({package} {pinned}):")
    for item in items:
        print(f"  {item}")
    status = 1
sys.exit(status)
EOF
