# Feature: kiro-agent-harness-template, Property 16: Quality hook passes only the saved path
# Validates: kiro-agent-harness-template/R6.2, kiro-agent-harness-template/R6.3
import json
import re
import unittest

from hypothesis import given, strategies as st

from tests.property import _profiles  # noqa: F401
from tests._support import TemplateCopy, run_script

TEST_FILE_REGEX = re.compile(r"(^|/)(test_[^/]+\.py|[^/]+_test\.go|[^/]+\.(test|spec)\.[jt]sx?)$")
# Records the arguments after the label, and CI, as JSON in $REC/<label>.
RECORDER = """#!/bin/sh
label=$1
shift
python3 -c 'import json, os, sys; open(os.environ["REC"] + sys.argv[1], "w").write(json.dumps({"argv": sys.argv[2:], "ci": os.environ.get("CI")}))' "$label" "$@"
"""

stems = st.text(alphabet="ab c'\"$;`&|()x-", min_size=1, max_size=12).filter(lambda s: s.strip())
paths = st.builds(
    lambda d, prefix, stem, suffix: d + prefix + stem + suffix,
    st.sampled_from(["", "src/", "src/my dir/"]),
    st.sampled_from(["", "test_"]),
    stems,
    st.sampled_from([".py", ".ts", ".test.ts", ".spec.js", "_test.go", ".go"]),
)


class QualitySavedPath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._copy = TemplateCopy()
        cls.root = cls._copy.__enter__()
        cls.rec = cls.root / "recordings"
        cls.rec.mkdir()
        (cls.root / "recorder.sh").write_text(RECORDER)
        (cls.root / "scripts/project-commands.env").write_text(
            'LINT_FILE_COMMAND="sh recorder.sh lint"\nTEST_FILE_COMMAND="sh recorder.sh test"\nTEST_COMMAND=""\n'
        )

    @classmethod
    def tearDownClass(cls):
        cls._copy.__exit__(None, None, None)

    @given(paths)
    def test_lint_gets_only_the_path_and_tests_run_only_for_test_files(self, path):
        for old in self.rec.iterdir():
            old.unlink()
        result = run_script(
            self.root / ".kiro/hooks/scripts/quality-on-save.sh",
            json.dumps({"hook_event_name": "PostFileSave", "file_path": path}).encode(),
            env={"REC": str(self.rec) + "/"},
            cwd=self.root,
        )
        self.assertEqual(result.returncode, 0, result.stdout.decode() + result.stderr.decode())
        self.assertEqual(json.loads((self.rec / "lint").read_text()), {"argv": [path], "ci": "true"})
        test_file = self.rec / "test"
        if TEST_FILE_REGEX.search(path):
            self.assertEqual(json.loads(test_file.read_text()), {"argv": [path], "ci": "true"})
        else:
            self.assertFalse(test_file.exists())


if __name__ == "__main__":
    unittest.main()
