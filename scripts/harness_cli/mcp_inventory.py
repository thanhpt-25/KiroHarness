"""MCP tool inventories (agent-harness-platform R10.2 to R10.4).

``harness/mcp/<server>.tools.json`` records each tool's SHA-256 over its name,
description and input schema for the pinned version, so a silently changed
server shows up as a diff. Generating or comparing against a live server needs
the server to run (``uvx``), so those commands are opt-in; the validator only
reads the recorded files.
"""

from __future__ import annotations

import hashlib
import json
import os
import queue
import subprocess
import threading

from harness_validator.report import error

PROTOCOL = "2025-06-18"
TIMEOUT = 90


def inventory_path(server: str) -> str:
    return f"harness/mcp/{server}.tools.json"


def tool_hash(tool: dict) -> str:
    canonical = json.dumps({"name": tool.get("name"), "description": tool.get("description", ""), "inputSchema": tool.get("inputSchema", {})},
                           sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build(server: str, package: str, version: str, tools: list) -> dict:
    return {"server": server, "package": package, "version": version, "tools": {t["name"]: tool_hash(t) for t in sorted(tools, key=lambda t: t["name"])}}


def diff(recorded: dict, live: dict) -> list:
    """Human-readable differences between two ``tools`` maps; empty when equal."""
    out = []
    for name in sorted(set(recorded) | set(live)):
        if name not in live:
            out.append(f"tool removed: {name}")
        elif name not in recorded:
            out.append(f"tool added: {name}")
        elif recorded[name] != live[name]:
            out.append(f"tool changed: {name}")
    return out


def fetch_tools(command: list, env=None, cwd=None, timeout: float = TIMEOUT) -> list:
    """Start an MCP server on stdio, run the handshake and return its ``tools/list`` result."""
    full_env = dict(os.environ)
    full_env.update(env or {})
    proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=full_env, cwd=cwd, text=True)
    lines: queue.Queue = queue.Queue()
    threading.Thread(target=lambda: [lines.put(line) for line in proc.stdout], daemon=True).start()

    def send(message):
        proc.stdin.write(json.dumps(message) + "\n")
        proc.stdin.flush()

    def receive(request_id):
        while True:
            try:
                message = json.loads(lines.get(timeout=timeout))
            except queue.Empty:
                raise TimeoutError(f"no response to request {request_id} within {timeout}s") from None
            except ValueError:
                continue
            if message.get("id") == request_id:
                if "error" in message:
                    raise RuntimeError(f"server error: {message['error']}")
                return message["result"]

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
              "params": {"protocolVersion": PROTOCOL, "capabilities": {}, "clientInfo": {"name": "harness-inventory", "version": "1"}}})
        receive(1)
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        tools, cursor, request_id = [], None, 2
        while True:
            send({"jsonrpc": "2.0", "id": request_id, "method": "tools/list", "params": {"cursor": cursor} if cursor else {}})
            result = receive(request_id)
            tools.extend(result.get("tools", []))
            cursor = result.get("nextCursor")
            if not cursor:
                return tools
            request_id += 1
    finally:
        proc.kill()
        proc.wait()
        proc.stdin.close()
        proc.stdout.close()


def server_command(item: dict) -> list:
    return [item.get("runner", "uvx"), f"{item['package']}@{item['version']}", *item["args"]]


def check_auto_approve(root) -> list:
    """Findings for autoApprove entries missing from a recorded inventory, and for stale inventories."""
    try:
        with open(os.path.join(root, "harness/manifest.json"), encoding="utf-8") as handle:
            servers = json.load(handle)["mcp"]
    except (OSError, ValueError, KeyError):
        return []
    findings = []
    for name, item in sorted(servers.items()):
        path = inventory_path(name)
        try:
            with open(os.path.join(root, path), encoding="utf-8") as handle:
                recorded = json.load(handle)
        except FileNotFoundError:
            continue
        except ValueError as exc:
            findings.append(error(path, "-", "MCP-INVENTORY", f"not valid JSON: {exc}"))
            continue
        if recorded.get("version") != item["version"]:
            findings.append(error(path, "version", "MCP-INVENTORY", f"inventory is for version {recorded.get('version')} but the Manifest pins {item['version']}; regenerate it"))
        for tool in item["auto_approve"]:
            if tool not in recorded.get("tools", {}):
                findings.append(error(path, f"autoApprove.{tool}", "MCP-INVENTORY", f'server "{name}": autoApprove tool "{tool}" is not in the tool inventory'))
    return findings


def run(root, servers: dict, only, check: bool, out, fetch=fetch_tools) -> int:
    """Write (or with ``check`` compare) inventories. Return the exit code."""
    status = 0
    for name, item in sorted(servers.items()):
        if only and name not in only:
            continue
        try:
            tools = fetch(server_command(item), env=item.get("env"), cwd=str(root))
        except Exception as exc:  # a server that cannot start is a finding, not a crash
            out.write(f"{name}: could not list tools: {exc}\n")
            status = 1
            continue
        live = build(name, item["package"], item["version"], tools)
        path = os.path.join(root, inventory_path(name))
        if check:
            try:
                with open(path, encoding="utf-8") as handle:
                    recorded = json.load(handle)
            except (OSError, ValueError):
                out.write(f"{name}: no inventory at {inventory_path(name)}\n")
                status = 1
                continue
            for line in diff(recorded.get("tools", {}), live["tools"]):
                out.write(f"{name}: {line}\n")
                status = 1
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(json.dumps(live, indent=2) + "\n")
            out.write(f"wrote {inventory_path(name)} ({len(live['tools'])} tools)\n")
    return status
