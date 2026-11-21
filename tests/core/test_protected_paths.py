"""Protected-path guard (agent-harness-platform R11.1, R11.2, R11.3, R11.5)."""
# Validates: agent-harness-platform/R11.1, agent-harness-platform/R11.2, agent-harness-platform/R11.3, agent-harness-platform/R11.5
import json
import unittest

from tests._support import ROOT, TemplateCopy, run_script
from tests.core.test_guard_cli import guard, native  # noqa: F401  (shared helpers)

import protected_paths

RULES = protected_paths.load_list(ROOT / "harness/policy/protected-paths.txt")


def decide(agent, subject_tool, tool_input):
    code, out, err = guard(agent, "pre_tool", native(agent, subject_tool, tool_input))
    return code, out, err


class PathMatching(unittest.TestCase):
    def test_defaults_protect_secrets_and_keep_the_example_file(self):
        for path in (".env", "app/.env", ".env.local", "keys/server.pem", "a/b.key", "id_rsa", "id_rsa.pub", "home/.ssh/config",
                     ".ssh", "x/.aws/credentials", ".kiro/settings/mcp.local.json", "src/../.env", "SRC/.ENV", "./.env", "C:\\proj\\.env"):
            with self.subTest(path=path):
                self.assertIsNotNone(protected_paths.protecting_rule(RULES, path))
        for path in (".env.example", "docs/.env.example", "src/app.py", "environment.md", ".aws/config", "x/key.txt", ".kiro/settings/mcp.json"):
            with self.subTest(path=path):
                self.assertIsNone(protected_paths.protecting_rule(RULES, path))

    def test_shell_reads_of_protected_paths(self):
        for command in ("cat .env", "less ./config/.env.local", "head -n 5 server.pem", "tail -f .ssh/id_rsa", "cp .env /tmp/x",
                        "base64 id_rsa", "xxd secret.key", "source .env", ". .env", "cat < .env", "echo hi && cat .env", "x=$(cat .env)",
                        "sudo cat /home/u/.aws/credentials", "grep KEY .env"):
            with self.subTest(command=command):
                self.assertIsNotNone(protected_paths.shell_read_target(command, RULES))
        for command in ("cat README.md", "cat .env.example", "ls -la", "echo .env", "git status", "cp a.txt b.txt"):
            with self.subTest(command=command):
                self.assertIsNone(protected_paths.shell_read_target(command, RULES))

    def test_empty_or_bad_list_is_an_error(self):
        for text in ("", "# only comments\n", "!\n"):
            with self.assertRaises(protected_paths.ProtectedListError):
                protected_paths.parse_list(text)


class GuardDecisions(unittest.TestCase):
    def test_every_agent_denies_tool_access_and_names_the_path(self):
        for agent, read, write in (("kiro", "fs_read", "fs_write"), ("claude-code", "Read", "Write")):
            for tool in (read, write):
                with self.subTest(agent=agent, tool=tool):
                    code, out, err = decide(agent, tool, {"path": ".env", "file_path": ".env"})
                    self.assertEqual(code, 2)
                    self.assertIn(".env", err)
                    self.assertIn("protected-path-guard", err)
            code, _out, _err = decide(agent, read, {"path": ".env.example", "file_path": ".env.example"})
            self.assertEqual(code, 0)

    def test_kiro_delete_and_shell_reads_are_denied(self):
        self.assertEqual(decide("kiro", "delete_file", {"targetFile": "keys/a.pem"})[0], 2)
        self.assertEqual(decide("kiro", "execute_bash", {"command": "cat .env"})[0], 2)
        self.assertEqual(decide("claude-code", "Bash", {"command": "base64 .env"})[0], 2)
        self.assertEqual(decide("claude-code", "Bash", {"command": "cat README.md"})[0], 0)

    def test_missing_or_empty_list_denies_naming_the_file(self):
        for content in (None, "# nothing\n"):
            with TemplateCopy() as root:
                path = root / "harness/policy/protected-paths.txt"
                if content is None:
                    path.unlink()
                else:
                    path.write_text(content)
                payload = native("kiro", "fs_read", {"path": "src/a.py"})
                result = run_script(root / "harness/bin/guard", payload, args=["kiro", "pre_tool"], cwd=root)
                self.assertEqual(result.returncode, 2)
                self.assertIn("protected-paths.txt", result.stderr.decode())

    def test_kiro_wrapper_runs_only_this_guard(self):
        with TemplateCopy() as root:
            wrapper = root / ".kiro/hooks/scripts/protected-path-guard.sh"
            denied = run_script(wrapper, native("kiro", "fs_read", {"path": ".env"}), cwd=root)
            self.assertEqual(denied.returncode, 2)
            allowed = run_script(wrapper, native("kiro", "execute_bash", {"command": "terraform apply"}), cwd=root)
            self.assertEqual((allowed.returncode, allowed.stdout), (0, b""))  # risky guard is not part of this wrapper


class Egress(unittest.TestCase):
    def test_web_fetch_to_an_unlisted_host_asks_for_every_agent(self):
        for agent, tool, key in (("kiro", "web_fetch", "url"), ("claude-code", "WebFetch", "url")):
            for url, expected in (("https://evil.example.net/x", "ask"), ("https://docs.aws.amazon.com/a", None), ("https://sub.pypi.org/a", None)):
                with self.subTest(agent=agent, url=url):
                    code, out, _ = decide(agent, tool, {key: url})
                    self.assertEqual(code, 0)
                    if expected:
                        self.assertEqual(json.loads(out)["hookSpecificOutput"]["permissionDecision"], "ask")
                    else:
                        self.assertEqual(out, "")

    def test_allowlist_file_change_takes_effect(self):
        with TemplateCopy() as root:
            (root / "harness/policy/egress-allowlist.txt").write_text("example.net\n")
            payload = native("claude-code", "WebFetch", {"url": "https://evil.example.net/x"})
            result = run_script(root / "harness/bin/guard", payload, args=["claude-code", "pre_tool"], cwd=root)
            self.assertEqual(result.stdout, b"")


if __name__ == "__main__":
    unittest.main()
