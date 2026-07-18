"""Run the local VNeGuide HTTP API."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path

import uvicorn


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local VNeGuide Chat API")
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Explicit LLM environment file, for example .env",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    if args.env_file is not None:
        os.environ["VNEGUIDE_LLM_ENV_FILE"] = str(args.env_file.resolve())
    host = os.environ.get("VNEGUIDE_API_HOST", "127.0.0.1")
    port = int(os.environ.get("VNEGUIDE_API_PORT", "8000"))
    uvicorn.run("vneguide.api.app:create_app", factory=True, host=host, port=port)


if __name__ == "__main__":
    main()
