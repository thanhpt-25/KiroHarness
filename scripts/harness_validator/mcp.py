"""MCP_Config checks."""

from __future__ import annotations

import json
import re

from .report import error, warning
from .secrets import SECRET_REF_SPAN_RE, is_secret_reference

CREDENTIAL_KEY_RE = re.compile(r"(?i)(key|token|secret|password|passwd|credential|auth)")
MUTATING_VERB_RE = re.compile(
    r"(?i)(write|create|delete|remove|commit|add|reset|checkout|push|exec|run|shell|move|rename)"
)
PIN_RE = re.compile(
    r"^(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?(?:\[[A-Za-z0-9,._-]+\])?)"
    r"@(?P<version>[0-9]+\.[0-9]+\.[0-9]+)$"
)
GIT_PACKAGE = "mcp-server-git"


def normalize_package(name: str) -> str:
    name = re.sub(r"\[.*\]$", "", name)
    return re.sub(r"[-_.]+", "-", name).lower()


def version_tuple(version: str) -> tuple:
    return tuple(int(part) for part in version.split("."))


def package_spec_index(args: list):
    """Return the index in ``args`` that holds the uvx package spec, or None."""
    for index, arg in enumerate(args):
        if arg == "--from":
            return index + 1 if index + 1 < len(args) else None
        if isinstance(arg, str) and arg.startswith("--from="):
            return index
    return 0 if args else None


def _spec_value(arg: str) -> str:
    return arg[len("--from=") :] if arg.startswith("--from=") else arg


def _check_pin(path, server, entry, config) -> tuple:
    """Return (findings, package name or None)."""
    args = entry.get("args")
    field = f"mcpServers.{server}.args"
    if not isinstance(args, list) or not args or not all(isinstance(a, str) for a in args):
        return [error(path, field, "MCP-PIN", f'server "{server}": uvx args must be a list of strings starting with a pinned package <name>@X.Y.Z')], None
    index = package_spec_index(args)
    if index is None:
        return [error(path, field, "MCP-PIN", f'server "{server}": --from has no package spec')], None
    spec = _spec_value(args[index])
    match = PIN_RE.match(spec)
    field = f"{field}[{index}]"
    if not match:
        return [
            error(
                path,
                field,
                "MCP-PIN",
                f'server "{server}": uvx package {spec!r} must be pinned to one exact version as <name>@X.Y.Z '
                "(no ranges, wildcards, latest, or unversioned names)",
            )
        ], None
    package = normalize_package(match.group("name"))
    minimums = {normalize_package(k): v for k, v in config.mcp_minimum_versions.items()}
    floor = minimums.get(package)
    if floor is not None:
        try:
            too_low = version_tuple(match.group("version")) < version_tuple(floor)
        except ValueError:
            too_low = False
        if too_low:
            return [
                error(
                    path,
                    field,
                    "MCP-PIN",
                    f'server "{server}": {package} {match.group("version")} is below the minimum version {floor} '
                    "set in scripts/validator-config.json",
                )
            ], package
    return [], package


def _check_git_scope(path, server, entry) -> list:
    args = entry.get("args")
    field = f"mcpServers.{server}.args"
    if not isinstance(args, list):
        return []
    strings = [a for a in args if isinstance(a, str)]
    value = None
    for index, arg in enumerate(strings):
        if arg == "--repository" and index + 1 < len(strings):
            value = strings[index + 1]
            break
        if arg.startswith("--repository="):
            value = arg[len("--repository=") :]
            break
    problems = []
    if value is None:
        problems.append("args must include --repository followed by . or an absolute path")
    elif not (value == "." or value.startswith("/") or re.match(r"^[A-Za-z]:[\\/]", value)):
        problems.append(f"--repository {value!r} must be . or an absolute path")
    if any(".." in re.split(r"[\\/=]", a) for a in strings):
        problems.append("args must not contain a parent-relative path (..)")
    return [
        error(path, field, "MCP-GIT-SCOPE", f'server "{server}": {p}, so the git server stays inside the workspace repository')
        for p in problems
    ]


def _references(entry, server, prefix=None):
    """Yield (variable, field path) for every Secret_Reference in an entry."""
    prefix = prefix or f"mcpServers.{server}"
    if isinstance(entry, str):
        for match in SECRET_REF_SPAN_RE.finditer(entry):
            yield match.group(1), prefix
    elif isinstance(entry, dict):
        for key, value in entry.items():
            yield from _references(value, server, f"{prefix}.{key}")
    elif isinstance(entry, list):
        for index, value in enumerate(entry):
            yield from _references(value, server, f"{prefix}[{index}]")


def _names_server(comment: str, server: str) -> bool:
    return re.search(r"(?<![\w-])" + re.escape(server) + r"(?![\w-])", comment) is not None


def check_mcp(path: str, text: str, env_example, config, native: bool = False) -> list:
    """``native`` is for an Agent's own MCP file (``.mcp.json``), which has no ``disabled`` field."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [error(path, f"line {exc.lineno}, column {exc.colno}", "MCP-JSON", f"not parseable JSON: {exc.msg}")]
    if not isinstance(data, dict) or not isinstance(data.get("mcpServers"), dict):
        return [error(path, "mcpServers", "MCP-SCHEMA", "top-level value must be an object with an mcpServers object")]

    findings = []
    references = {}  # variable -> list of (server, field)
    for server, entry in data["mcpServers"].items():
        prefix = f"mcpServers.{server}"
        if not isinstance(entry, dict):
            findings.append(error(path, prefix, "MCP-SCHEMA", f'server "{server}": entry must be an object'))
            continue

        disabled = entry.get("disabled")
        if native:
            pass
        elif "disabled" not in entry:
            findings.append(error(path, f"{prefix}.disabled", "MCP-DISABLED", f'server "{server}": disabled field is missing; set it to true or false'))
        elif not isinstance(disabled, bool):
            findings.append(error(path, f"{prefix}.disabled", "MCP-DISABLED", f'server "{server}": disabled must be a JSON boolean, got {json.dumps(disabled)}'))

        package = None
        command = entry.get("command")
        if isinstance(command, str) and command.rsplit("/", 1)[-1] == "uvx":
            pin_findings, package = _check_pin(path, server, entry, config)
            findings.extend(pin_findings)

        if package == GIT_PACKAGE or (package is None and server == "git"):
            findings.extend(_check_git_scope(path, server, entry))

        env = entry.get("env")
        if env is not None and not isinstance(env, dict):
            findings.append(error(path, f"{prefix}.env", "MCP-SCHEMA", f'server "{server}": env must be an object'))
        elif isinstance(env, dict):
            for key, value in env.items():
                if CREDENTIAL_KEY_RE.search(key) and not is_secret_reference(value):
                    findings.append(
                        error(
                            path,
                            f"{prefix}.env.{key}",
                            "MCP-SECRET-REF",
                            f'server "{server}": credential value for {key} must be a Secret_Reference like ' + "${VAR_NAME}" + ", not a literal",
                        )
                    )

        auto = entry.get("autoApprove")
        if auto is not None and not isinstance(auto, list):
            findings.append(error(path, f"{prefix}.autoApprove", "MCP-SCHEMA", f'server "{server}": autoApprove must be a list of tool names'))
        elif isinstance(auto, list):
            for index, tool in enumerate(auto):
                field = f"{prefix}.autoApprove[{index}]"
                if not isinstance(tool, str):
                    findings.append(error(path, field, "MCP-SCHEMA", f'server "{server}": autoApprove items must be strings'))
                elif tool in config.read_only_allowlist:
                    continue
                elif tool in config.known_mutating_tools or MUTATING_VERB_RE.search(tool):
                    findings.append(error(path, field, "MCP-AUTOAPPROVE", f'server "{server}": tool "{tool}" can change files, repository state, or run commands and must not be auto-approved'))
                else:
                    findings.append(warning(path, field, "MCP-AUTOAPPROVE-UNKNOWN", f'server "{server}": tool "{tool}" is not on the read-only allowlist'))

        for variable, field in _references(entry, server):
            references.setdefault(variable, []).append((server, field))

    for variable in sorted(references):
        uses = references[variable]
        servers = sorted({s for s, _ in uses})
        field = uses[0][1]
        names = ", ".join(f'"{s}"' for s in servers)
        if env_example is None or variable not in env_example:
            findings.append(error(path, field, "MCP-ENV-EXAMPLE", f"variable {variable} used by server {names} is not listed in .env.example"))
            continue
        var = env_example.variables[variable]
        if len(var.lines) > 1:
            findings.append(error(path, field, "MCP-ENV-EXAMPLE", f"variable {variable} is listed {len(var.lines)} times in .env.example (lines {', '.join(map(str, var.lines))})"))
        if not any(_names_server(c, s) for c in var.comments for s in servers):
            findings.append(error(path, field, "MCP-ENV-EXAMPLE", f"variable {variable} in .env.example needs a comment directly above it naming server {names}"))
    return findings
