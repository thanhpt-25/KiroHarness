"""Smoke tests for the shipped Template content (Requirements 1, 2, 4.1, 5.1,
6.1, 6.5, 7.4, 8.1, 8.2, 8.7, 12, 13)."""

import json
import os
import re
import shutil
import stat
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests._support import ROOT, SCRIPTS, detail
from harness_validator import frontmatter, globmatch, placeholders, secrets

DIRECTORIES = [
    ".kiro/steering", ".kiro/hooks", ".kiro/hooks/scripts", ".kiro/settings",
    ".kiro/specs", ".kiro/specs/example-feature", "scripts", "docs",
]
FILES = [
    "README.md", "docs/CUSTOMIZING.md", ".env.example", ".gitignore", ".kiro/settings/mcp.json",
    ".kiro/specs/example-feature/requirements.md", ".kiro/specs/example-feature/design.md",
    ".kiro/specs/example-feature/tasks.md",
]
STEERING = ROOT / ".kiro/steering"
SPEC = ROOT / ".kiro/specs/example-feature"
EARS = [
    r"^WHEN .+, THE \w+ SHALL .+",
    r"^WHILE .+, THE \w+ SHALL .+",
    r"^IF .+, THEN THE \w+ SHALL .+",
    r"^WHERE .+, THE \w+ SHALL .+",
    r"^THE \w+ SHALL .+",
]


def shell_scripts():
    return sorted((ROOT / ".kiro/hooks/scripts").glob("*.sh")) + sorted(SCRIPTS.glob("*.sh"))


def meta(name):
    return frontmatter.parse_front_matter(frontmatter.split_front_matter((STEERING / name).read_text())[0])


def hook(name):
    return json.loads((ROOT / ".kiro/hooks" / name).read_text())["hooks"][0]


class Layout(unittest.TestCase):
    def test_required_directories_hold_files(self):
        for directory in DIRECTORIES:
            with self.subTest(directory=directory):
                path = ROOT / directory
                self.assertTrue(path.is_dir())
                # Git tracks files, not directories, so nested files count.
                self.assertTrue(any(p.is_file() for p in path.rglob("*")), f"{directory} has no files")

    def test_required_files_are_non_empty(self):
        for name in FILES:
            with self.subTest(file=name):
                path = ROOT / name
                self.assertTrue(path.is_file(), f"{name} is missing")
                self.assertGreater(path.stat().st_size, 0)

    @unittest.skipIf(shutil.which("git") is None, "git is not installed")
    def test_gitignore_rules(self):
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(["git", "init", "-q", tmp], check=True)
            shutil.copy(ROOT / ".gitignore", Path(tmp) / ".gitignore")

            def ignored(path):
                return subprocess.run(["git", "-C", tmp, "check-ignore", "-q", path]).returncode == 0

            for path in (".env", ".env.local", ".env.production", ".kiro/settings/mcp.local.json"):
                with self.subTest(path=path):
                    self.assertTrue(ignored(path), detail(path, "ignored", "not ignored"))
            for path in (".env.example", ".kiro/settings/mcp.json"):
                with self.subTest(path=path):
                    self.assertFalse(ignored(path), detail(path, "not ignored", "ignored"))

    def test_scripts_are_executable_with_a_shebang(self):
        for path in shell_scripts():
            with self.subTest(script=path.name):
                self.assertTrue(path.stat().st_mode & stat.S_IXUSR, f"{path} lacks the owner execute bit")
                self.assertTrue(path.read_text().startswith("#!"), f"{path} has no interpreter line")

    def test_git_records_scripts_as_executable(self):
        if shutil.which("git") is None:
            self.skipTest("git is not installed")
        listing = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-s"], capture_output=True, text=True)
        if listing.returncode != 0 or not listing.stdout:
            self.skipTest("the Template is not a git repository")
        modes = {line.split("\t", 1)[1]: line.split()[0] for line in listing.stdout.splitlines()}
        for path in shell_scripts():
            rel = path.relative_to(ROOT).as_posix()
            if rel in modes:
                with self.subTest(script=rel):
                    self.assertEqual(modes[rel], "100755")


class Steering(unittest.TestCase):
    def test_required_files_and_inclusion_modes(self):
        expected = {
            "product.md": "always", "tech.md": "always", "structure.md": "always", "security.md": "always",
            "testing.md": "fileMatch", "coding-standards.md": "fileMatch",
        }
        for name, mode in expected.items():
            with self.subTest(file=name):
                self.assertEqual(meta(name)["inclusion"], mode)

    def test_manual_and_auto_examples_exist(self):
        modes = {meta(p.name).get("inclusion") for p in STEERING.glob("*.md")}
        self.assertTrue({"manual", "auto"} <= modes)

    def test_auto_files_have_name_and_description(self):
        for path in STEERING.glob("*.md"):
            data = meta(path.name)
            if data.get("inclusion") == "auto":
                with self.subTest(file=path.name):
                    self.assertTrue(1 <= len(data["name"]) <= 64)
                    self.assertTrue(1 <= len(data["description"]) <= 200)

    def test_file_match_patterns_select_the_example_paths(self):
        testing = meta("testing.md")["fileMatchPattern"]
        coding = meta("coding-standards.md")["fileMatchPattern"]
        for path, expected in [("src/app.test.ts", True), ("src/app.spec.js", True), ("tests/test_app.py", True),
                               ("test/app_test.go", True), ("src/app.ts", False), ("README.md", False)]:
            with self.subTest(pattern="testing", path=path):
                self.assertEqual(globmatch.match_any(testing, path), expected)
        for path, expected in [("src/app.ts", True), ("src/app.tsx", True), ("src/app.js", True), ("src/app.py", True),
                               ("src/app.go", True), ("README.md", False), (".env.example", False),
                               (".kiro/settings/mcp.json", False)]:
            with self.subTest(pattern="coding", path=path):
                self.assertEqual(globmatch.match_any(coding, path), expected)

    def test_security_rules_have_their_own_headings(self):
        headings = re.findall(r"^## (.+)$", (STEERING / "security.md").read_text(), re.M)
        self.assertEqual(headings, ["Least Privilege", "Secrets Through Environment Variables",
                                    "Input Validation at Trust Boundaries", "Confirm Before Destructive Actions"])


class Hooks(unittest.TestCase):
    def test_destructive_guard_matches_only_shell_tools(self):
        matcher = re.compile(hook("destructive-command-guard.json")["matcher"])
        for tool in ("execute_bash", "execute_pwsh", "control_bash_process"):
            self.assertTrue(matcher.fullmatch(tool))
        for tool in ("read_file", "fs_write", "delete_file", "web_fetch", "execute_bash_extra"):
            self.assertFalse(matcher.search(tool), tool)

    def test_risky_guard_matcher_covers_every_listed_tool(self):
        matcher = re.compile(hook("risky-tool-guard.json")["matcher"])
        conf = (ROOT / ".kiro/hooks/scripts/risky-tools.conf").read_text()
        tools = {line.split(" | ")[0].strip() for line in conf.splitlines() if line.strip() and not line.startswith("#")}
        for tool in tools:
            self.assertTrue(matcher.fullmatch(tool), tool)

    def test_default_risky_list_covers_deletion_fetch_and_deploy(self):
        conf = (ROOT / ".kiro/hooks/scripts/risky-tools.conf").read_text()
        self.assertRegex(conf, r"(?m)^delete_file \|")
        self.assertRegex(conf, r"(?m)^web_fetch \|.*host-not-in")
        self.assertRegex(conf, r"(?m)^execute_bash \| Deploy")

    def test_quality_hook_matcher_and_timeout(self):
        definition = hook("quality-on-save.json")
        self.assertEqual(definition["trigger"], "PostFileSave")
        self.assertLessEqual(definition["timeout"], 120)
        matcher = re.compile(definition["matcher"])
        self.assertTrue(matcher.search("src/app.py"))
        self.assertFalse(matcher.search("README.md"))

    def test_lifecycle_hook_timeouts(self):
        self.assertLessEqual(hook("session-start-context.json")["timeout"], 10)
        self.assertLessEqual(hook("prompt-secret-scan.json")["timeout"], 5)
        self.assertLessEqual(hook("post-task-tests.json")["timeout"], 300)

    def test_stop_prompt_names_the_validation_command(self):
        definition = hook("stop-validate.json")
        self.assertEqual(definition["trigger"], "Stop")
        self.assertEqual(definition["action"]["type"], "agent")
        self.assertIn("scripts/validate.sh", definition["action"]["prompt"])
        self.assertIn("code 0", definition["action"]["prompt"])

    def test_examples_are_disabled(self):
        for path in (ROOT / ".kiro/hooks/examples").glob("*.json"):
            with self.subTest(file=path.name):
                self.assertIs(json.loads(path.read_text())["hooks"][0]["enabled"], False)


class Mcp(unittest.TestCase):
    def setUp(self):
        path = ROOT / ".kiro/settings/mcp.json"
        if not path.is_file():
            self.fail(".kiro/settings/mcp.json is missing")
        self.servers = json.loads(path.read_text())["mcpServers"]

    def test_three_uvx_servers(self):
        self.assertEqual(set(self.servers), {"aws-docs", "fetch", "git"})
        for name, entry in self.servers.items():
            with self.subTest(server=name):
                self.assertEqual(entry["command"], "uvx")
                self.assertIsInstance(entry["disabled"], bool)

    def test_servers_without_credentials_are_enabled(self):
        for name, entry in self.servers.items():
            needs_credential = any("${" in str(v) for v in entry.get("env", {}).values())
            with self.subTest(server=name):
                self.assertEqual(entry["disabled"], needs_credential)

    def test_git_server_is_confined_to_the_workspace(self):
        args = self.servers["git"]["args"]
        self.assertEqual(args[args.index("--repository") + 1], ".")


class ExampleSpec(unittest.TestCase):
    def test_files_have_heading_and_body(self):
        for name in ("requirements.md", "design.md", "tasks.md"):
            text = (SPEC / name).read_text()
            with self.subTest(file=name):
                self.assertRegex(text, r"(?m)^#+ ")
                self.assertRegex(text, r"(?m)^[^#\s].+")

    def test_requirements_structure_and_ears(self):
        text = (SPEC / "requirements.md").read_text()
        self.assertIn("## Introduction", text)
        self.assertIn("## Glossary", text)
        glossary = set(re.findall(r"^- \*\*(\w+)\*\*", text, re.M))
        requirements = re.split(r"(?m)^### Requirement \d+", text)[1:]
        self.assertGreaterEqual(len(requirements), 2)
        for block in requirements:
            self.assertRegex(block, r"\*\*User Story:\*\* As an? .+, I want .+, so that .+")
            criteria = re.findall(r"(?m)^\d+\. (.+)$", block)
            self.assertGreaterEqual(len(criteria), 2)
            for criterion in criteria:
                with self.subTest(criterion=criterion):
                    self.assertTrue(any(re.match(p, criterion) for p in EARS), f"not an EARS pattern: {criterion}")
                    for name in re.findall(r"THE (\w+) SHALL", criterion):
                        self.assertIn(name, glossary)

    def test_design_sections(self):
        text = (SPEC / "design.md").read_text()
        for section in ("Overview", "Architecture", "Components and Interfaces", "Data Models", "Error Handling", "Testing Strategy"):
            self.assertRegex(text, rf"(?m)^## {section}$")

    def test_tasks_reference_every_requirement(self):
        requirements = (SPEC / "requirements.md").read_text()
        defined = set()
        for number, block in re.findall(r"(?m)^### Requirement (\d+)(.*?)(?=^### |\Z)", requirements, re.S):
            for criterion in re.findall(r"(?m)^(\d+)\. ", block):
                defined.add(f"{number}.{criterion}")
        tasks = (SPEC / "tasks.md").read_text()
        items = re.findall(r"(?m)^\s*- \[[ x]\] .+", tasks)
        self.assertTrue(items)
        referenced = set(re.findall(r"\b(\d+\.\d+)\b", " ".join(re.findall(r"_Requirements: ([^_]+)_", tasks))))
        self.assertTrue(referenced <= defined, referenced - defined)
        self.assertEqual(defined - referenced, set())


class Documentation(unittest.TestCase):
    readme = (ROOT / "README.md").read_text()
    guide = (ROOT / "docs/CUSTOMIZING.md").read_text()

    def test_readme_lists_every_directory(self):
        for directory in DIRECTORIES:
            self.assertIn(f"`{directory}/`", self.readme)

    def test_readme_setup_steps_in_order(self):
        steps = self.readme.split("## Setup", 1)[1]
        positions = [steps.index(s) for s in ("1. Copy the Template", "2. Copy `.env.example`", "3. Replace every", "4. In `.kiro/settings/mcp.json`", "5. Run the validation command")]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("scripts/validate.sh", steps)
        self.assertIn("must not be committed", self.readme)
        self.assertIn("exits with code 0", self.readme)

    def test_readme_lists_every_placeholder(self):
        listed = placeholders.readme_placeholder_list(self.readme)
        files, _ = placeholders.tracked_text_files(ROOT)
        for path in files:
            if path.name == "README.md" and path.parent == ROOT:
                continue
            for name in placeholders.find_placeholders(path.read_text(encoding="utf-8")):
                with self.subTest(placeholder=name, file=str(path.relative_to(ROOT))):
                    self.assertIn(name, listed)

    def test_guide_has_one_section_per_inclusion_mode(self):
        for mode in ("always", "fileMatch", "manual", "auto"):
            self.assertRegex(self.guide, rf"(?m)^### Inclusion mode `{mode}`$")

    def test_guide_hook_section(self):
        for text in ("SessionStart", "PostFileDelete", '"tool_name"', "Exit code 0 allows", "Exit code 2 blocks", '"permissionDecision":"ask"'):
            self.assertIn(text, self.guide)

    def test_guide_mcp_section(self):
        self.assertIn("${EXAMPLE_SERVICE_TOKEN}", self.guide)
        self.assertIn('"disabled": true', self.guide)
        self.assertRegex(self.guide, r"@\d+\.\d+\.\d+\"")
        self.assertIn(".env.example", self.guide)

    def test_guide_guard_list_section(self):
        for text in ("destructive-commands.txt", "risky-tools.conf", "To add an entry", "To remove an entry", "Run `scripts/validate.sh` after any change"):
            self.assertIn(text, self.guide)

    def test_docs_contain_no_secret_values(self):
        config = secrets.load_validator_config(SCRIPTS / "validator-config.json")
        for name, text in (("README.md", self.readme), ("docs/CUSTOMIZING.md", self.guide)):
            for number, line in enumerate(text.splitlines(), start=1):
                with self.subTest(file=name, line=number):
                    self.assertEqual(secrets.find_secrets(line, config.secret_patterns), [])


if __name__ == "__main__":
    unittest.main()
