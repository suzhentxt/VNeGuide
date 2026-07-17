from __future__ import annotations

import unittest

from vneguide.cli.runtime import CliConfigurationError, load_session_factory


class RuntimeIntegrationTest(unittest.TestCase):
    def test_loads_callable_factory(self) -> None:
        factory = load_session_factory("tests.integration.fixtures:create_session")
        session = factory()

        self.assertTrue(callable(session.send))

    def test_rejects_invalid_factory_path(self) -> None:
        with self.assertRaisesRegex(CliConfigurationError, "package.module:factory"):
            load_session_factory("not-a-valid-path")

    def test_reports_missing_attribute_without_import_traceback(self) -> None:
        with self.assertRaisesRegex(CliConfigurationError, "chưa cung cấp factory"):
            load_session_factory("tests.integration.fixtures:missing_factory")


if __name__ == "__main__":
    unittest.main()
