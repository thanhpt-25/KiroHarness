# Feature: kiro-agent-harness-template, Property 13: Destructive list loading
import tempfile
import unittest
from pathlib import Path

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests import _support  # noqa: F401
from destructive_guard import ListLoadError, load_patterns

pattern_line = st.text(alphabet="abcdefg -/=*~", min_size=1, max_size=15).filter(lambda s: s.strip() and not s.strip().startswith("#"))
noise = st.sampled_from(["", "   ", "# a comment", "  # indented comment", "\t"])


@st.composite
def list_files(draw):
    count = draw(st.sampled_from([0, 1, 2, 199, 200, 201]))
    patterns = [draw(pattern_line) for _ in range(min(count, 3))] + [f"cmd{i} --x" for i in range(max(0, count - 3))]
    lines = []
    for pattern in patterns:
        lines.extend(draw(st.lists(noise, max_size=2)))
        lines.append(draw(st.sampled_from(["", " ", "  "])) + pattern + draw(st.sampled_from(["", " "])))
    lines.extend(draw(st.lists(noise, max_size=2)))
    return patterns, "\n".join(lines)


class DestructiveListLoad(unittest.TestCase):
    @given(list_files())
    def test_returns_the_patterns_or_raises_naming_the_file(self, case):
        patterns, text = case
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "list.txt"
            path.write_text(text)
            if 1 <= len(patterns) <= 200:
                self.assertEqual([p.text for p in load_patterns(path)], [p.strip() for p in patterns])
            else:
                with self.assertRaises(ListLoadError) as ctx:
                    load_patterns(path)
                self.assertIn(str(path), str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
