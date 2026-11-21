# Feature: agent-harness-platform, Property 29: Adapter round trip
# Validates: agent-harness-platform/R4.2, agent-harness-platform/R4.6
import unittest

from hypothesis import given

from tests.property import _profiles  # noqa: F401
from tests.property.strategies_core import adapter, native_payloads


class AdapterRoundTrip(unittest.TestCase):
    @given(native_payloads())
    def test_decode_of_built_payload_equals_the_decoded_event(self, case):
        agent, trigger, raw = case
        ad = adapter(agent)
        event = ad.decode(raw, trigger)
        self.assertEqual(ad.decode(ad.build_native_payload(event), trigger), event)


if __name__ == "__main__":
    unittest.main()
