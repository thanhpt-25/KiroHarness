"""Config_Validator entry point: ``python3 -m harness_validator --root <workspace>``.

Exit 0 with no errors, 1 with errors, 2 on an internal crash outside the checkers.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import sys
import traceback
from pathlib import Path

from . import envfile, hook_rules, hookconfig, mcp, placeholders, report, secrets, steering, verification
from .report import error, warning

MCP_PATH = ".kiro/settings/mcp.json"
CONFIG_PATH = "scripts/validator-config.json"
LIB_DIR = "harness/core"
DESTRUCTIVE_LIST = "harness/policy/destructive-commands.txt"
RISKY_LIST = "harness/policy/risky-tools.conf"
RISKY_SCRIPT = "risky-tool-guard.sh"
README = "README.md"


class Run:
    """Collects findings and the set of files checked during one validator run."""

    def __init__(self, root: Path):
        self.root = root
        self.findings = []
        self.files = set()

    def rel(self, path: Path) -> str:
        try:
            return path.relative_to(self.root).as_posix()
        except ValueError:
            return path.as_posix()

    def guarded(self, checker: str, path: str, func, *args):
        """Call ``func``; turn an exception into an [INTERNAL] error and keep going."""
        try:
            result = func(*args)
        except Exception as exc:  # one checker bug must not hide other findings
            self.findings.append(
                error(path, "-", "INTERNAL", f"{checker} crashed: {exc.__class__.__name__}: {exc}")
            )
            return None
        if isinstance(result, list):
            self.findings.extend(result)
        return result


def _read_text(path: Path):
    """Return (text, problem)."""
    try:
        return path.read_bytes().decode("utf-8"), None
    except OSError as exc:
        return None, f"file could not be read: {exc.strerror or exc}"
    except UnicodeDecodeError as exc:
        return None, f"file is not valid UTF-8 (byte {exc.start})"


def _secret_findings(path: str, pairs, patterns) -> list:
    findings = []
    for field, value in pairs:
        for hit in secrets.find_secrets(value, patterns):
            findings.append(
                error(
                    path,
                    field,
                    "SECRET",
                    f'value matches secret pattern "{hit.pattern_id}": {secrets.mask(hit.value)}; '
                    "use a Secret_Reference like ${VAR_NAME} instead",
                )
            )
    return findings


def _line_pairs(text: str):
    for number, line in enumerate(text.splitlines(), start=1):
        yield f"line {number}", line


def _json_pairs(text: str):
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, RecursionError):
        return []
    return list(secrets.walk_json_strings(data))


def load_lib_module(root: Path, name: str):
    """Load a guard module from harness/core so parsing logic is shared."""
    lib = root / LIB_DIR
    path = lib / f"{name}.py"
    if not path.is_file():
        raise FileNotFoundError(f"{LIB_DIR}/{name}.py not found")
    added = str(lib) not in sys.path
    if added:
        sys.path.insert(0, str(lib))
    try:
        for dependency in ("hookio",):
            sys.modules.pop(dependency, None)
        module_name = f"_harness_lib_{name}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        module = importlib.util.module_from_spec(spec)
        # dataclasses look the module up in sys.modules while the class is created.
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(module_name, None)
            raise
        return module
    finally:
        if added:
            sys.path.remove(str(lib))
        sys.modules.pop("hookio", None)


# --- checkers -------------------------------------------------------------


def check_steering_files(run: Run, patterns) -> None:
    directory = run.root / ".kiro/steering"
    for path in sorted(directory.glob("*.md")) if directory.is_dir() else []:
        rel = run.rel(path)
        run.files.add(rel)
        text, problem = _read_text(path)
        if text is None:
            run.findings.append(error(rel, "-", "STEER-FM", problem))
            continue
        run.guarded("steering", rel, steering.check_steering, rel, text)
        if patterns is not None:
            run.guarded("secret scan", rel, _secret_findings, rel, _line_pairs(text), patterns)


def hook_file_paths(root: Path) -> list:
    paths = []
    for directory in (root / ".kiro/hooks", root / ".kiro/hooks/examples"):
        if directory.is_dir():
            paths.extend(sorted(p for p in directory.glob("*.json") if p.is_file()))
    return paths


def check_hook_files(run: Run, patterns) -> None:
    for path in hook_file_paths(run.root):
        rel = run.rel(path)
        run.files.add(rel)
        try:
            data = path.read_bytes()
        except OSError as exc:
            run.findings.append(error(rel, "-", "HOOK-JSON", f"file could not be read: {exc.strerror or exc}"))
            continue
        run.guarded("hook rules", rel, hook_rules.check_hook_file, rel, data, run.root)
        if patterns is not None:
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                continue
            run.guarded("secret scan", rel, _secret_findings, rel, _json_pairs(text), patterns)


def check_mcp_file(run: Run, config) -> None:
    path = run.root / MCP_PATH
    if not path.is_file():
        run.findings.append(error(MCP_PATH, "-", "MCP-MISSING", f"MCP_Config not found at expected path {MCP_PATH}"))
        return
    run.files.add(MCP_PATH)
    text, problem = _read_text(path)
    if text is None:
        run.findings.append(error(MCP_PATH, "-", "MCP-JSON", problem))
        return
    env_example = None
    env_path = run.root / ".env.example"
    if env_path.is_file():
        run.files.add(".env.example")
        env_text, _ = _read_text(env_path)
        if env_text is not None:
            env_example = envfile.parse_env_example(env_text)
    if config is None:
        return
    run.guarded("mcp", MCP_PATH, mcp.check_mcp, MCP_PATH, text, env_example, config)
    run.guarded("secret scan", MCP_PATH, _secret_findings, MCP_PATH, _json_pairs(text), config.secret_patterns)


def check_verification_records(run: Run) -> None:
    directory = run.root / "docs/verification"
    for path in sorted(directory.glob("*/*/*.md")) if directory.is_dir() else []:
        rel = run.rel(path)
        run.files.add(rel)
        text, problem = _read_text(path)
        if text is None:
            run.findings.append(error(rel, "-", "VERIFY-FM", problem))
            continue
        run.guarded("verification record", rel, verification.check_record, rel, text)


def check_destructive_list(run: Run) -> list:
    run.files.add(DESTRUCTIVE_LIST)
    guard = load_lib_module(run.root, "destructive_guard")
    try:
        guard.load_patterns(run.root / DESTRUCTIVE_LIST)
    except guard.ListLoadError as exc:
        return [error(DESTRUCTIVE_LIST, "-", "DESTR-LIST", f"Destructive_Command_List {exc.reason}")]
    return []


def risky_guard_matchers(root: Path) -> list:
    """Return the matchers of every Hook_Definition that runs risky-tool-guard.sh."""
    matchers = []
    for path in hook_file_paths(root):
        try:
            hook_file = hookconfig.parse_hook_file(path)
        except hookconfig.HookError:
            continue
        for definition in hook_file.hooks:
            command = definition.action.command
            if isinstance(command, str) and RISKY_SCRIPT in command and definition.enabled is not False:
                matchers.append(definition.matcher or "")
    return matchers


def check_risky_list(run: Run) -> list:
    run.files.add(RISKY_LIST)
    guard = load_lib_module(run.root, "risky_guard")
    path = run.root / RISKY_LIST
    text, problem = _read_text(path)
    if text is None:
        return [error(RISKY_LIST, "-", "RISKY-LIST", f"Risky_Tool_List {problem}")]
    try:
        entries = guard.parse_list(text)
    except guard.RiskyListError as exc:
        field = f"line {exc.line_no}" if exc.line_no else "-"
        return [error(RISKY_LIST, field, "RISKY-LIST", f"Risky_Tool_List: {exc.detail}")]
    findings = []
    lines = text.splitlines()
    for entry in entries:
        above = lines[entry.line_no - 2].strip() if entry.line_no >= 2 else ""
        match = re.match(r"^#\s*example:\s*(.*)$", above)
        problem = None
        if not match:
            problem = "needs an '# example: <json tool_input>' comment on the line directly above it"
        else:
            try:
                example = json.loads(match.group(1))
                if not isinstance(example, dict):
                    problem = "example comment must hold a JSON object"
                elif not guard.matches(entry, entry.tool, example):
                    problem = "example tool_input does not match the entry"
            except json.JSONDecodeError as exc:
                problem = f"example comment is not valid JSON: {exc.msg}"
        if problem:
            findings.append(error(RISKY_LIST, f"line {entry.line_no}", "RISKY-LIST", f"entry for {entry.tool}: {problem}"))

    matchers = risky_guard_matchers(run.root)
    if not matchers:
        findings.append(error(RISKY_LIST, "-", "RISKY-COVER", f"no enabled Hook_File in .kiro/hooks/ runs {RISKY_SCRIPT}"))
        return findings
    compiled = []
    for matcher in matchers:
        try:
            compiled.append(re.compile(matcher))
        except re.error:
            continue  # reported by hook_rules
    for entry in entries:
        if not any(c.fullmatch(entry.tool) for c in compiled):
            findings.append(
                error(
                    RISKY_LIST,
                    f"line {entry.line_no}",
                    "RISKY-COVER",
                    f"tool {entry.tool} is not covered by the Risky_Tool_Guard matcher",
                )
            )
    return findings


def check_placeholders(run: Run) -> list:
    findings = []
    files, used_fallback = placeholders.tracked_text_files(run.root)
    if used_fallback:
        findings.append(
            warning(".", "-", "PLACEHOLDER-SCAN", "git is unavailable or this is not a git repository; the placeholder scan walked the file tree instead of using git ls-files")
        )
    readme_path = run.root / README
    readme_text, _ = _read_text(readme_path) if readme_path.is_file() else (None, None)
    listed = placeholders.readme_placeholder_list(readme_text or "")
    found = {}  # name -> sorted list of files
    for path in files:
        rel = run.rel(path)
        run.files.add(rel)
        if rel == README:
            continue
        text, _ = _read_text(path)
        if text is None:
            continue
        for name in placeholders.find_placeholders(text):
            found.setdefault(name, []).append(rel)
    for name in sorted(found):
        paths = sorted(found[name])
        if name not in listed:
            findings.append(
                error(
                    paths[0],
                    "{{" + name + "}}",
                    "PLACEHOLDER",
                    f"placeholder {{{{{name}}}}} is not listed in the README.md ## Placeholders section; found in: {', '.join(paths)}",
                )
            )
    for name, doc in sorted(listed.items()):
        actual = set(found.get(name, []))
        if not actual:
            findings.append(warning(README, f"line {doc.line}", "PLACEHOLDER-STALE", f"placeholder {{{{{name}}}}} is listed but no file contains it"))
            continue
        for listed_path in doc.files:
            if listed_path not in actual:
                findings.append(warning(README, f"line {doc.line}", "PLACEHOLDER-STALE", f"placeholder {{{{{name}}}}} is listed for {listed_path}, which does not contain it"))
        for missing in sorted(actual - set(doc.files)):
            findings.append(warning(README, f"line {doc.line}", "PLACEHOLDER-STALE", f"placeholder {{{{{name}}}}} also appears in {missing}, which the list does not name"))
    return findings


def validate(root) -> tuple:
    """Run every check. Return ``(findings, files_checked)``."""
    root = Path(root).resolve()
    run = Run(root)
    config = None
    try:
        config = secrets.load_validator_config(root / CONFIG_PATH)
    except secrets.ConfigError as exc:
        run.findings.append(error(CONFIG_PATH, "-", "CONFIG", str(exc)))
    run.files.add(CONFIG_PATH)
    patterns = config.secret_patterns if config else None

    check_steering_files(run, patterns)
    check_hook_files(run, patterns)
    check_mcp_file(run, config)
    check_verification_records(run)
    run.guarded("destructive list", DESTRUCTIVE_LIST, check_destructive_list, run)
    run.guarded("risky list", RISKY_LIST, check_risky_list, run)
    run.guarded("placeholder scan", README, check_placeholders, run)
    return run.findings, len(run.files)


def main(argv=None, stdout=None) -> int:
    stdout = stdout or sys.stdout
    parser = argparse.ArgumentParser(prog="harness_validator", description=__doc__)
    parser.add_argument("--root", default=".", help="workspace root (default: current directory)")
    args = parser.parse_args(argv)
    try:
        findings, files_checked = validate(args.root)
        text, code = report.render(findings, files_checked)
    except Exception:
        traceback.print_exc()
        return 2
    stdout.write(text)
    return code


if __name__ == "__main__":
    sys.exit(main())
