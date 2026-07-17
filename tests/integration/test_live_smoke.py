from __future__ import annotations

import os
import unittest

import pytest

from vneguide.cli.runtime import load_session_factory

pytestmark = pytest.mark.live


def _live_key_is_configured() -> bool:
    provider = os.getenv("VNEGUIDE_LLM_PROVIDER", "mock").strip().lower()
    key_name = "VNEGUIDE_LITELLM_API_KEY" if provider == "litellm" else "VNEGUIDE_API_KEY"
    return bool(os.getenv(key_name))


@unittest.skipUnless(
    os.getenv("VNEGUIDE_RUN_LIVE_SMOKE") == "1" and _live_key_is_configured(),
    "Live session smoke is opt-in and requires the selected provider key.",
)
class LiveProviderSmokeTest(unittest.TestCase):
    def test_provider_returns_a_turn_result(self) -> None:
        session = load_session_factory()()
        result = session.send("Tôi cần xin bản sao trích lục khai sinh.")

        self.assertTrue(getattr(result, "reply", ""))
        self.assertTrue(getattr(result, "source_ids", []))


if __name__ == "__main__":
    unittest.main()
