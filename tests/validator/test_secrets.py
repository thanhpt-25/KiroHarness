"""Secret patterns (Requirements 10.6, 13.10).

Sample values are assembled at run time so that no file in the repository
contains a string that looks like a real credential.
"""
# Validates: kiro-agent-harness-template/R10.6, kiro-agent-harness-template/R13.10

import unittest

from tests._support import SCRIPTS
from harness_validator import secrets

CONFIG = secrets.load_validator_config(SCRIPTS / "validator-config.json")

SAMPLES = {
    "aws-access-key-id": "AKIA" + "Q" * 16,
    "github-token": "ghp" + "_" + "a1" * 18,
    "github-fine-grained-pat": "github" + "_pat_" + "B2" * 31,
    "slack-token": "xox" + "b-" + "1234567890-abc",
    "private-key": "-----BEGIN " + "RSA PRIVATE KEY-----",
    "openai-style-key": "sk" + "-" + "z9" * 12,
    "google-api-key": "AIza" + "S" * 35,
    "stripe-live-key": "sk" + "_live_" + "c3" * 12,
    "generic-assignment": "api" + "_key = " + "x7" * 10,
}


class SecretPatterns(unittest.TestCase):
    def test_every_configured_pattern_has_a_sample(self):
        self.assertEqual({p.id for p in CONFIG.secret_patterns}, set(SAMPLES))

    def test_each_pattern_matches_its_sample(self):
        for pattern_id, value in SAMPLES.items():
            with self.subTest(pattern=pattern_id):
                hits = secrets.find_secrets(value, CONFIG.secret_patterns)
                self.assertIn(pattern_id, {h.pattern_id for h in hits})

    def test_secret_references_are_not_reported(self):
        for value in ("${GITHUB_TOKEN}", "${A}", "Bearer ${API_TOKEN}", "token=${SERVICE_API_KEY_VALUE_1}"):
            with self.subTest(value=value):
                self.assertEqual(secrets.find_secrets(value, CONFIG.secret_patterns), [])

    def test_placeholder_values_are_not_matched(self):
        for value in ("replace-me", "EXAMPLE_SERVICE_TOKEN=replace-me", "your-token-here", "changeme", "{{" + "API_KEY}}"):
            with self.subTest(value=value):
                self.assertEqual(secrets.find_secrets(value, CONFIG.secret_patterns), [])

    def test_mask_keeps_at_most_four_characters(self):
        self.assertEqual(secrets.mask("abcdefghij"), "abcd******")
        self.assertEqual(secrets.mask("abc"), "a**")
        self.assertEqual(secrets.mask(""), "")

    def test_walk_json_strings_yields_field_paths(self):
        obj = {"a": {"b": ["x", {"c": "y"}]}, "n": 1}
        self.assertEqual(list(secrets.walk_json_strings(obj)), [("a.b[0]", "x"), ("a.b[1].c", "y")])


if __name__ == "__main__":
    unittest.main()
