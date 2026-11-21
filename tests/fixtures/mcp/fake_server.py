"""A tiny MCP server on stdio for inventory tests. FAKE_TOOLS (JSON) overrides the tool list."""
import json
import os
import sys

TOOLS = json.loads(os.environ.get("FAKE_TOOLS", "null")) or [
    {"name": "read_x", "description": "Read x", "inputSchema": {"type": "object"}},
    {"name": "write_x", "description": "Write x", "inputSchema": {"type": "object", "properties": {"v": {"type": "string"}}}},
]
for line in sys.stdin:
    msg = json.loads(line)
    if "id" not in msg:
        continue
    if msg["method"] == "initialize":
        result = {"protocolVersion": "2025-06-18", "capabilities": {"tools": {}}, "serverInfo": {"name": "fake", "version": "1"}}
    else:
        result = {"tools": TOOLS}
    print(json.dumps({"jsonrpc": "2.0", "id": msg["id"], "result": result}), flush=True)
