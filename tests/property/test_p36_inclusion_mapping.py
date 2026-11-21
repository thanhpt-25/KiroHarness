# Feature: agent-harness-platform, Property 36: Inclusion mapping preserves selection
# Validates: agent-harness-platform/R7.1
import re
import unittest

from hypothesis import HealthCheck, given, settings, strategies as st

from tests.property import _profiles  # noqa: F401
from tests.generator._fixture import MANIFEST, SourceRoot, run_cli, with_agents
from harness_validator import frontmatter, globmatch

SEGMENTS = st.sampled_from(["src", "tests", "docs", "app", "a.b"])
NAMES = st.sampled_from(["x", "test_x", "x.test", "x.spec", "y_test"])
EXTENSIONS = st.sampled_from(["py", "ts", "tsx", "go", "md"])

patterns = st.one_of(
    st.builds(lambda exts: "**/*.{" + ",".join(exts) + "}", st.lists(EXTENSIONS, min_size=2, max_size=3, unique=True)),
    st.builds(lambda seg, ext: f"{seg}/**/*.{ext}", SEGMENTS, EXTENSIONS),
    st.builds(lambda name: f"**/{name}.*", NAMES),
    st.builds(lambda ext: f"*.{ext}", EXTENSIONS),
    st.builds(lambda seg: f"{seg}/**", SEGMENTS),
)
paths = st.builds(lambda dirs, name, ext: "/".join([*dirs, f"{name}.{ext}"]), st.lists(SEGMENTS, max_size=3), NAMES, EXTENSIONS)


def rendered_patterns(root, agent):
    if agent == "claude-code":
        text = (root / ".claude/rules/probe.md").read_text()
        return re.findall(r'^  - "(.*)"$', text, re.M)
    if agent == "cursor":
        line = re.search(r"^globs: (.*)$", (root / ".cursor/rules/probe.mdc").read_text(), re.M).group(1)
        return line.split(", ")
    text = (root / ".github/instructions/probe.instructions.md").read_text()
    return re.search(r'^applyTo: "(.*)"$', text, re.M).group(1).split(",")


class InclusionMapping(unittest.TestCase):
    @settings(suppress_health_check=[HealthCheck.too_slow], max_examples=40)
    @given(st.lists(patterns, min_size=1, max_size=3, unique=True), st.lists(paths, min_size=1, max_size=8))
    def test_rendered_rule_selects_exactly_the_paths_the_source_selects(self, source_patterns, sample):
        quoted = ", ".join('"%s"' % p for p in source_patterns)
        with SourceRoot(with_agents(claude_code=True, cursor=True, copilot=True)) as root:
            (root / "harness/guidance/probe.md").write_text(f"---\ninclusion: fileMatch\nfileMatchPattern: [{quoted}]\n---\n\n# Probe\n")
            self.assertEqual(run_cli(root, "sync")[0], 0)
            data = frontmatter.parse_front_matter(frontmatter.split_front_matter((root / "harness/guidance/probe.md").read_text())[0])
            self.assertEqual(data["fileMatchPattern"], source_patterns)
            for agent in ("claude-code", "cursor", "copilot"):
                rendered = rendered_patterns(root, agent)
                for path in sample:
                    with self.subTest(agent=agent, path=path, patterns=source_patterns):
                        self.assertEqual(globmatch.match_any(rendered, path), globmatch.match_any(source_patterns, path))


if __name__ == "__main__":
    unittest.main()
