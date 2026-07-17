from __future__ import annotations

import os
import unittest

import pytest

from vneguide.cli.runtime import load_session_factory

pytestmark = pytest.mark.live


@unittest.skipUnless(
    os.getenv("VNEGUIDE_RUN_LIVE_SMOKE") == "1" and bool(os.getenv("VNEGUIDE_API_KEY")),
    "Live smoke test is opt-in and requires VNEGUIDE_API_KEY.",
)
class LiveProviderSmokeTest(unittest.TestCase):
    def test_provider_returns_a_turn_result(self) -> None:
        session = load_session_factory()()
        result = session.send("Tôi cần xin bản sao trích lục khai sinh.")

        self.assertTrue(getattr(result, "reply", ""))
        self.assertTrue(getattr(result, "source_ids", []))


if __name__ == "__main__":
    unittest.main()
