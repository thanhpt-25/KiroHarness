# Feature: kiro-agent-harness-template, Property 10: Destructive guard agrees with the reference matcher
import io
import tempfile
import unittest
from pathlib import Path

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests._support import tool_call
import destructive_guard

ALPHABET = ["rm", "-rf", "/", "git", "push", "--force", "drop", "table", "x", "main"]
tokens = st.lists(st.sampled_from(ALPHABET), min_size=1, max_size=5)
whitespace = st.sampled_from([" ", "  ", "\t", " \t "])


def reference_blocks(pattern_lines, command):
    """Plain loop: does some pattern's word list occur in order in the command's words?"""
    words = command.lower().split()
    for line in pattern_lines:
        wanted = line.lower().split()
        i = 0
        for word in words:
            if i < len(wanted) and word == wanted[i]:
                i += 1
        if i == len(wanted):
            return line
    return None


@st.composite
def commands(draw):
    parts = draw(tokens)
    out = ""
    for index, part in enumerate(parts):
        cased = "".join(c.upper() if draw(st.booleans()) else c for c in part)
        out += (draw(whitespace) if index else draw(st.sampled_from(["", " "]))) + cased
    return out + draw(st.sampled_from(["", " ", "\t"]))


class DestructiveReference(unittest.TestCase):
    @given(st.lists(tokens.map(" ".join), min_size=1, max_size=5, unique=True), commands())
    def test_blocks_iff_the_reference_matches(self, pattern_lines, command):
        with tempfile.TemporaryDirectory() as tmp:
            list_path = Path(tmp) / "list.txt"
            list_path.write_text("# comment\n" + "\n".join(pattern_lines) + "\n")
            stderr = io.StringIO()
            code = destructive_guard.main(io.BytesIO(tool_call("execute_bash", {"command": command})), stderr, list_path)
        expected = reference_blocks(pattern_lines, command)
        if expected is None:
            self.assertEqual((code, stderr.getvalue()), (0, ""))
        else:
            self.assertEqual(code, 2)
            self.assertIn("Destructive_Command_List", stderr.getvalue())
            matched = stderr.getvalue().split('matched pattern "', 1)[1].split('"', 1)[0]
            self.assertIn(matched, pattern_lines)
            self.assertIsNotNone(reference_blocks([matched], command))


if __name__ == "__main__":
    unittest.main()
