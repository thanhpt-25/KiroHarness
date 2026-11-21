"""Payload probe masking, path normalization, and import (Requirements 3.1, 11.4)."""
# Validates: agent-harness-platform/R3.1, agent-harness-platform/R11.4

import io
import json
import re
import tempfile
import unittest
from pathlib import Path

from tests._support import HOOK_SCRIPTS, ROOT, TemplateCopy, detail, run_script  # noqa: F401  (sys.path setup)

import payload_probe  # noqa: E402
from prompt_scan import load_patterns  # noqa: E402

CONFIG = ROOT / "scripts" / "validator-config.json"


def secret_samples():
    """One sample per pattern, assembled at run time so no literal secret is in the repository."""
    return {
        "aws-access-key-id": "AKIA" + "ABCDEFGHIJKLMNOP",
        "github-token": "ghp_" + "a" * 36,
        "slack-token": "xoxb-" + "1234567890-abcdef",
        "private-key": "-----BEGIN " + "RSA PRIVATE KEY-----",
        "openai-style-key": "sk-" + "A1b2C3d4E5f6G7h8I9j0K1",
    }


class Masking(unittest.TestCase):
    def setUp(self):
        self.patterns = load_patterns(CONFIG)

    def test_secret_values_keep_four_characters_and_are_masked(self):
        for pattern_id, secret in secret_samples().items():
            text = json.dumps({"prompt": f"use {secret} now"})
            out = payload_probe.sanitize(text.encode(), self.patterns, Path("/nowhere"), None)
            self.assertNotIn(secret, out, detail(pattern_id, "secret absent", out))
            self.assertIn(secret[:4] + "*", out, detail(pattern_id, "first 4 characters kept", out))

    def test_workspace_and_home_paths_are_replaced(self):
        root = Path("/Users/someone/Projects/App")
        text = json.dumps({"cwd": str(root), "file_path": f"{root}/src/a.py", "note": "/Users/someone/.config/x"})
        out = payload_probe.sanitize(text.encode(), self.patterns, root, "/Users/someone")
        data = json.loads(out)
        self.assertEqual(data["cwd"], "/WORKSPACE")
        self.assertEqual(data["file_path"], "/WORKSPACE/src/a.py")
        self.assertEqual(data["note"], "/HOME/.config/x")


class Probe(unittest.TestCase):
    def run_probe(self, root, args, stdin=b"{}"):
        out, err = io.StringIO(), io.StringIO()
        code = payload_probe.main(args, io.BytesIO(stdin), err, root=root, config_path=CONFIG, home=None, stdout=out)
        return code, out.getvalue(), err.getvalue()

    def test_records_masked_payload_under_the_trigger_and_never_blocks(self):
        secret = secret_samples()["github-token"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = json.dumps({"prompt": secret, "cwd": str(root)}).encode()
            code, out, err = self.run_probe(root, ["UserPromptSubmit"], payload)
            self.assertEqual((code, out, err), (0, "", ""))
            files = list((root / ".harness" / "probe" / "UserPromptSubmit").glob("*.json"))
            self.assertEqual(len(files), 1)
            text = files[0].read_text()
            self.assertNotIn(secret, text)
            self.assertEqual(json.loads(text)["cwd"], "/WORKSPACE")

    def test_bad_trigger_name_writes_nothing_outside_the_probe_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            code, _out, err = self.run_probe(root, ["../../etc"])
            self.assertEqual(code, 0)
            self.assertIn("usage", err)
            self.assertEqual([p for p in root.rglob("*") if p.is_file()], [])

    def test_unloadable_patterns_record_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out, err = io.StringIO(), io.StringIO()
            code = payload_probe.main(["PreToolUse"], io.BytesIO(b"{}"), err, root=root,
                                      config_path=root / "missing.json", stdout=out)
            self.assertEqual(code, 0)
            self.assertEqual([p for p in root.rglob("*.json")], [])

    def test_wrapper_exits_zero_and_prints_nothing(self):
        with TemplateCopy() as root:
            result = run_script(root / ".kiro/hooks/scripts/payload-probe.sh", b'{"a": 1}', cwd=root)
            self.assertEqual((result.returncode, result.stdout), (0, b""))

    def test_import_copies_masked_records_into_the_version_directory(self):
        secret = secret_samples()["aws-access-key-id"]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            record = root / ".harness" / "probe" / "PreToolUse"
            record.mkdir(parents=True)
            (record / "r1.json").write_text(json.dumps({"x": secret}))
            (record / "bad.json").write_text("not json")
            code, out, err = self.run_probe(root, ["--import", "1.2.3"])
            self.assertEqual(code, 0, err)
            target = root / "tests/fixtures/payloads/kiro/1.2.3/PreToolUse/r1.json"
            self.assertTrue(target.exists())
            self.assertNotIn(secret, target.read_text())
            self.assertFalse((target.parent / "bad.json").exists())
            self.assertRegex(out, r"imported 1 record\(s\).*skipped 1")

    def test_import_rejects_unsafe_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, _o, _e = self.run_probe(Path(tmp), ["--import", "../x"])
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
