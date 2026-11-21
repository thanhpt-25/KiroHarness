"""Shared Hypothesis profiles for the property test suite.

Import this module before defining property tests:

    from tests.property import _profiles  # noqa: F401

The ``default`` profile runs 100 examples per test. The ``ci`` profile runs 300.
Select a profile with the ``HYPOTHESIS_PROFILE`` environment variable.
``deadline=None`` avoids flaky failures in tests that start subprocesses.
"""

import os

from hypothesis import settings

DEFAULT_PROFILE = "default"
CI_PROFILE = "ci"

settings.register_profile(DEFAULT_PROFILE, max_examples=100, deadline=None)
settings.register_profile(CI_PROFILE, max_examples=300, deadline=None)

PROFILE = os.environ.get("HYPOTHESIS_PROFILE", "").strip() or DEFAULT_PROFILE

# Raises InvalidArgument for an unknown profile name, so a typo fails loudly.
settings.load_profile(PROFILE)
