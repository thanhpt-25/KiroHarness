"""Test runner used by scripts/validate.sh.

Runs every test in the given directories, even after a failure, and prints
for each failure the test name and the assertion message, which the tests
write as input, expected result, and actual result.
"""

from __future__ import annotations

import json
import os
import sys
import unittest


class DetailedResult(unittest.TextTestResult):
    outcomes: dict = {}  # test id -> [status, reason]; written to build/test-results.json

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes.setdefault(test.id(), ["passed", ""])

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.outcomes[test.id()] = ["skipped", reason]

    def _report(self, kind: str, test, err) -> None:
        exc_type, exc, _tb = err
        self.stream.writeln(f"{kind}: {test.id()}")
        if exc_type is not None and issubclass(exc_type, AssertionError):
            message = str(exc)
        else:
            message = self._exc_info_to_string(err, test)
        for line in message.rstrip().splitlines():
            self.stream.writeln(f"    {line}")
        self.stream.flush()

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.outcomes[test.id()] = ["failed", ""]
        self._report("FAIL", test, err)

    def addError(self, test, err):
        super().addError(test, err)
        self.outcomes[test.id()] = ["failed", ""]
        self._report("ERROR", test, err)

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            kind = "FAIL" if issubclass(err[0], test.failureException) else "ERROR"
            self._report(kind, subtest, err)

    def printErrors(self):
        # Failures were already printed with their details as they happened.
        pass


def run(start_dirs, top_level: str, stream=None) -> tuple:
    """Return ``(passed, failed)``. Errors and unexpected successes count as failed."""
    stream = stream or sys.stdout
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for start in start_dirs:
        suite.addTests(loader.discover(start, top_level_dir=top_level))
    DetailedResult.outcomes = {}
    runner = unittest.TextTestRunner(stream=stream, verbosity=1, resultclass=DetailedResult)
    result = runner.run(suite)
    failed_ids = {t.id() for t, _ in result.failures + result.errors}
    failed = len(result.failures) + len(result.errors) + len(result.unexpectedSuccesses)
    passed = result.testsRun - len(failed_ids) - len(result.skipped) - len(result.unexpectedSuccesses)
    return max(passed, 0), failed


def write_results(top_level: str) -> None:
    """Record every test outcome for ``scripts/harness trace``; never fails the run."""
    try:
        path = os.path.join(top_level, "build", "test-results.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(DetailedResult.outcomes, handle, indent=1, sort_keys=True)
    except OSError:
        pass


def main(argv) -> int:
    top_level, *start_dirs = argv
    # Resolve symlinks (macOS /var -> /private/var) so discovery sees one path.
    top_level = os.path.realpath(top_level)
    start_dirs = [os.path.realpath(os.path.join(top_level, d)) for d in start_dirs]
    passed, failed = run(start_dirs, top_level)
    write_results(top_level)
    print(f"TESTS-SUMMARY passed={passed} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
