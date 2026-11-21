# Feature: kiro-agent-harness-template, Property 12: Destructive guard fails closed on malformed input
import io
import json
import unittest

from hypothesis import assume, given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests._support import HOOK_SCRIPTS
import destructive_guard

LIST = HOOK_SCRIPTS / "destructive-commands.txt"


def not_json(data: bytes) -> bool:
    try:
        json.loads(data.decode("utf-8"))
        return False
    except (UnicodeDecodeError, ValueError):
        return True


malformed = st.one_of(
    st.just(b""),
    st.binary(max_size=40).filter(not_json),
    st.text(max_size=30).map(str.encode).filter(not_json),
    st.one_of(st.lists(st.integers()), st.integers(), st.text(), st.none()).map(lambda v: json.dumps(v).encode()),
    st.one_of(st.none(), st.just(""), st.just("   "), st.integers(), st.lists(st.text())).map(
        lambda c: json.dumps({"tool_name": "execute_bash", "tool_input": {"command": c}}).encode()
    ),
    st.just(json.dumps({"tool_name": "execute_bash", "tool_input": {}}).encode()),
    st.just(json.dumps({"tool_name": "control_bash_process", "tool_input": {"action": "start"}}).encode()),
)


class DestructiveFailClosed(unittest.TestCase):
    @given(malformed)
    def test_exits_2_with_a_parse_or_missing_command_message(self, stdin):
        stderr = io.StringIO()
        code = destructive_guard.main(io.BytesIO(stdin), stderr, LIST)
        self.assertEqual(code, 2, stdin)
        message = stderr.getvalue()
        self.assertTrue("could not be parsed" in message or "command field is missing" in message, message)


if __name__ == "__main__":
    unittest.main()
