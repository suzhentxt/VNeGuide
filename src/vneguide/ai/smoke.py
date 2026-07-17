"""Provider-only live smoke test that does not depend on core or CLI."""

from __future__ import annotations

import argparse
import math
from collections.abc import Sequence
from pathlib import Path

from .config import build_llm_provider, load_llm_config
from .providers import ProviderConfigurationError, ProviderError, StructuredRequest

_SMOKE_SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "boolean"}},
    "required": ["ok"],
    "additionalProperties": False,
}


def main(argv: Sequence[str] | None = None) -> int:
    """Run one synthetic structured extraction and emit only a safe summary."""

    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.confirm_live:
        parser.error("live network call requires --confirm-live")

    try:
        config = load_llm_config(env_file=args.env_file)
        if config.provider == "mock":
            raise ProviderConfigurationError("Live smoke requires a non-mock provider")
        provider = build_llm_provider(config)
    except ProviderConfigurationError as error:
        print(f"MODEL_SMOKE_CONFIG_ERROR: {error}")
        return 2

    request = StructuredRequest(
        system_prompt="Return only JSON matching the supplied schema.",
        user_prompt="Set ok to true.",
        json_schema=_SMOKE_SCHEMA,
        schema_name="vneguide_model_smoke",
        timeout_seconds=args.timeout,
    )
    try:
        result = provider.generate_structured(request)
    except ProviderError:
        print("MODEL_SMOKE_FAILED: provider_error")
        return 3
    if result != {"ok": True}:
        print("MODEL_SMOKE_FAILED: unexpected_output")
        return 4

    print(f"MODEL_SMOKE_OK provider={config.provider} model={config.model} structured_output=true")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one synthetic VNeGuide model call")
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="explicit env file to load (default: .env)",
    )
    parser.add_argument(
        "--timeout",
        type=_positive_float,
        default=45.0,
        help="provider timeout in seconds (default: 45)",
    )
    parser.add_argument(
        "--confirm-live",
        action="store_true",
        help="confirm that one synthetic prompt may be sent to the configured endpoint",
    )
    return parser


def _positive_float(value: str) -> float:
    try:
        parsed = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError("timeout must be a number") from None
    if not math.isfinite(parsed) or parsed <= 0:
        raise argparse.ArgumentTypeError("timeout must be a finite positive number")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
