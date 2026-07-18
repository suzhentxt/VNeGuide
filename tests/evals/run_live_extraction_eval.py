"""Opt-in live evaluator for context-aware structured extraction.

This command sends only the checked-in synthetic fixture to the configured model. Its
report contains aggregate metrics and provider/model names, never messages, raw model
responses, evidence text, credentials, or environment dumps.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from vneguide.ai import (
    ExtractionCatalog,
    ExtractionTurnContext,
    StructuredExtractor,
    build_llm_provider,
    load_llm_config,
)

from .extraction_evaluator import (
    evaluate_cases,
    load_cases,
    repository_state,
    verify_dataset_sha256,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CASES_PATH = (
    REPOSITORY_ROOT / "data" / "evaluation" / ("synthetic_multiturn_extraction.jsonl")
)
DATASET_CHECKSUM_PATH = (
    REPOSITORY_ROOT / "data" / "qa" / "synthetic_multiturn_extraction.jsonl.sha256"
)


def _turn_context(
    procedure_code: str | None,
    field_id: str | None,
) -> ExtractionTurnContext | None:
    if procedure_code is None:
        if field_id is not None:
            raise ValueError("An expected field requires an active procedure")
        return None
    return ExtractionTurnContext(procedure_code, field_id)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run aggregate extraction metrics on checked-in synthetic cases."
    )
    parser.add_argument(
        "--confirm-live",
        action="store_true",
        help="Required acknowledgement that this command calls a configured model provider.",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Optional, explicit LLM environment file; it is never included in the report.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional new JSON report path. Existing files are never overwritten.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = parser.parse_args(argv)
    if not arguments.confirm_live:
        parser.error("--confirm-live is required before any model request is sent")

    try:
        verified_digest = verify_dataset_sha256(
            DEFAULT_CASES_PATH.resolve(), DATASET_CHECKSUM_PATH.resolve()
        )
    except ValueError:
        parser.error("synthetic evaluation fixture integrity check failed")

    config = load_llm_config(env_file=arguments.env_file)
    if config.provider == "mock":
        parser.error("live evaluation requires a non-mock VNEGUIDE_LLM_PROVIDER")
    if config.model is None:
        parser.error("live evaluation requires VNEGUIDE_MODEL")

    cases_path = DEFAULT_CASES_PATH.resolve()
    cases = load_cases(cases_path)
    catalog = ExtractionCatalog.from_data_package(REPOSITORY_ROOT / "data")
    extractor = StructuredExtractor(build_llm_provider(config), catalog)
    revision, working_tree_dirty = repository_state(REPOSITORY_ROOT)
    report = evaluate_cases(
        extractor,
        cases,
        context_factory=_turn_context,
        provider=config.provider,
        model=config.model,
        dataset_id=cases_path.name,
        dataset_digest=verified_digest,
        revision=revision,
        working_tree_dirty=working_tree_dirty,
    )
    encoded = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if arguments.output is None:
        print(encoded)
    else:
        try:
            with arguments.output.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(encoded)
                stream.write("\n")
        except FileExistsError:
            parser.error("--output already exists; choose a new report path")
        except OSError:
            parser.error("--output could not be written")
        print(
            json.dumps(
                {
                    "case_count": report["case_count"],
                    "report_path": str(arguments.output),
                },
                ensure_ascii=False,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
