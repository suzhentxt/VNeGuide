"""Tests for the local HTTP API entry point."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vneguide.api.__main__ import main


class ApiMainTests(unittest.TestCase):
    def test_explicit_env_file_is_forwarded_to_the_session_factory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            env_file = Path(temporary_directory) / ".env"
            env_file.write_text("VNEGUIDE_LLM_PROVIDER=mock\n", encoding="utf-8")

            with (
                patch.dict(os.environ, {}, clear=True),
                patch("vneguide.api.__main__.uvicorn.run") as run,
            ):
                main(["--env-file", str(env_file)])

                self.assertEqual(
                    os.environ["VNEGUIDE_LLM_ENV_FILE"],
                    str(env_file.resolve()),
                )
                run.assert_called_once_with(
                    "vneguide.api.app:create_app",
                    factory=True,
                    host="127.0.0.1",
                    port=8000,
                )

    def test_process_environment_still_controls_host_and_port(self) -> None:
        environ = {
            "VNEGUIDE_API_HOST": "0.0.0.0",
            "VNEGUIDE_API_PORT": "8010",
        }
        with (
            patch.dict(os.environ, environ, clear=True),
            patch("vneguide.api.__main__.uvicorn.run") as run,
        ):
            main([])

            self.assertNotIn("VNEGUIDE_LLM_ENV_FILE", os.environ)
            run.assert_called_once_with(
                "vneguide.api.app:create_app",
                factory=True,
                host="0.0.0.0",
                port=8010,
            )


if __name__ == "__main__":
    unittest.main()
