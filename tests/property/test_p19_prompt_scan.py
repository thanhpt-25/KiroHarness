# Feature: kiro-agent-harness-template, Property 19: Prompt secret scan blocks exactly the prompts with secrets
import io
import json
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests._support import SCRIPTS
import prompt_scan

CONFIG = SCRIPTS / "validator-config.json"
PATTERNS = prompt_scan.load_patterns(CONFIG)
UP = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
DIG = "0123456789"
LOW = "abcdefghijklmnopqrstuvwxyz"


def chars(alphabet, n, m=None):
    return st.text(alphabet=alphabet, min_size=n, max_size=m or n)


def secret_values(pattern_id):
    """One hand-written strategy per secret pattern; values are generated, never real."""
    an = UP + LOW + DIG
    return {
        "aws-access-key-id": st.builds(lambda p, s: p + s, st.sampled_from(["AKIA", "ASIA"]), chars(UP + DIG, 16)),
        "github-token": st.builds(lambda c, s: "gh" + c + "_" + s, st.sampled_from("pousr"), chars(an, 36, 40)),
        "github-fine-grained-pat": chars(an + "_", 60, 64).map(lambda s: "github_pat_" + s),
        "slack-token": st.builds(lambda c, s: "xox" + c + "-" + s, st.sampled_from("abprs"), chars(an + "-", 10, 20)),
        "private-key": st.sampled_from(["RSA ", "EC ", "OPENSSH ", ""]).map(lambda k: "-----BEGIN " + k + "PRIVATE KEY-----"),
        "openai-style-key": chars(an + "_-", 20, 30).map(lambda s: "sk-" + s),
        # The pattern ends with \b, so the last character must be a word character.
        "google-api-key": st.builds(lambda s, e: "AIza" + s + e, chars(an + "_-", 34), chars(an, 1)),
        "stripe-live-key": st.builds(lambda c, s: c + "k_live_" + s, st.sampled_from("sr"), chars(an, 20, 24)),
        "generic-assignment": st.builds(lambda k, s: k + "=" + s, st.sampled_from(["api_key", "secret", "token", "password"]), chars(an, 16, 24)),
    }[pattern_id]


secrets_any = st.sampled_from([pid for pid, _ in PATTERNS]).flatmap(secret_values)
benign = st.text(alphabet=LOW + " .,?!", max_size=40)


def scan(prompt):
    stderr = io.StringIO()
    code = prompt_scan.main(io.BytesIO(json.dumps({"prompt": prompt}).encode()), stderr, CONFIG)
    return code, stderr.getvalue()


class PromptScan(unittest.TestCase):
    @given(benign, st.one_of(st.none(), secrets_any), benign)
    def test_blocks_exactly_prompts_with_a_secret(self, before, secret, after):
        prompt = before + (" " + secret + " " if secret else "") + after
        code, stderr = scan(prompt)
        matched = [pid for pid, regex in PATTERNS if regex.search(prompt)]
        if matched:
            self.assertEqual(code, 2)
            self.assertIn(f'"{matched[0]}"', stderr)
            if secret:
                self.assertNotIn(secret, stderr)
        else:
            self.assertEqual((code, stderr), (0, ""))
        if secret:
            self.assertTrue(matched, secret)


if __name__ == "__main__":
    unittest.main()
