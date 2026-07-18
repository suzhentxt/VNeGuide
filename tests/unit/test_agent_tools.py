"""Tests for the grounded fact-retrieval tools (Phase 1).

Every tool must return reviewed data plus ``source_ids`` traceable to the data
package. The LLM cannot author facts — these tests pin that contract.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from langchain_core.tools import BaseTool

from vneguide.agent import ToolContext, build_tools
from vneguide.data import ProcedureRepository
from vneguide.rules import ProcedureQAResponder, QuestionSelector, RuleEngine

ROOT = Path(__file__).resolve().parents[2]

_QA_TOOLS = [
    "get_procedure_fee",
    "get_processing_time",
    "get_required_documents",
    "get_required_information",
    "get_authority",
    "get_submission_channels",
    "get_result",
    "get_guidance_steps",
    "get_legal_basis",
    "get_conditions_and_limits",
]

PROCEDURE_CODES = ["1.004194", "1.013314", "2.000635"]


@pytest.fixture(scope="module")
def tools() -> dict[str, BaseTool]:
    repository = ProcedureRepository.discover(ROOT)
    ctx = ToolContext(
        repository=repository,
        qa_responder=ProcedureQAResponder(repository),
        rule_engine=RuleEngine(repository),
        question_selector=QuestionSelector(repository),
    )
    return {t.name: t for t in build_tools(ctx)}


def test_build_tools_returns_fifteen(tools: dict[str, BaseTool]) -> None:
    assert len(tools) == 15
    expected = {
        "get_procedure_fee",
        "get_processing_time",
        "get_required_documents",
        "get_required_information",
        "get_authority",
        "get_submission_channels",
        "get_result",
        "get_guidance_steps",
        "get_legal_basis",
        "get_conditions_and_limits",
        "get_field_help",
        "get_missing_fields",
        "validate_draft",
        "get_field_question",
        "list_procedures",
    }
    assert set(tools) == expected


def test_list_procedures_returns_all_three(tools: dict[str, BaseTool]) -> None:
    result = tools["list_procedures"].invoke({})
    assert isinstance(result, dict)
    procedures = result["procedures"]
    assert {p["code"] for p in procedures} == set(PROCEDURE_CODES)
    for proc in procedures:
        assert proc["name"]


@pytest.mark.parametrize("tool_name", _QA_TOOLS)
@pytest.mark.parametrize("code", PROCEDURE_CODES)
def test_qa_tools_return_text_and_source_ids(
    tools: dict[str, BaseTool], tool_name: str, code: str
) -> None:
    result = tools[tool_name].invoke({"procedure_code": code})
    assert isinstance(result, dict)
    assert result["text"], f"{tool_name}({code}) returned empty text"
    assert isinstance(result["source_ids"], list)
    assert result["source_ids"], f"{tool_name}({code}) returned no source_ids"


def test_get_field_help_returns_text_and_source_ids(tools: dict[str, BaseTool]) -> None:
    result = tools["get_field_help"].invoke(
        {"procedure_code": "2.000635", "field_id": "copies_requested"}
    )
    assert result["text"]
    assert isinstance(result["source_ids"], list)


def test_get_missing_fields_for_empty_draft(tools: dict[str, BaseTool]) -> None:
    result = tools["get_missing_fields"].invoke({"procedure_code": "1.004194", "draft_values": {}})
    assert isinstance(result["missing_field_ids"], list)
    assert "applicant_full_name" in result["missing_field_ids"]


def test_get_missing_fields_shrinks_as_values_filled(tools: dict[str, BaseTool]) -> None:
    empty = tools["get_missing_fields"].invoke({"procedure_code": "1.004194", "draft_values": {}})[
        "missing_field_ids"
    ]
    partial = tools["get_missing_fields"].invoke(
        {
            "procedure_code": "1.004194",
            "draft_values": {"applicant_full_name": "Nguyen Van A"},
        }
    )["missing_field_ids"]
    assert "applicant_full_name" in empty
    assert "applicant_full_name" not in partial
    assert len(partial) == len(empty) - 1


def test_validate_draft_returns_status_and_source_ids(tools: dict[str, BaseTool]) -> None:
    result = tools["validate_draft"].invoke({"procedure_code": "1.004194", "draft_values": {}})
    assert result["status"] in {"ready_to_submit", "incomplete", "invalid"}
    assert isinstance(result["issues"], list)
    assert isinstance(result["source_ids"], list)
    assert result["source_ids"]


def test_get_field_question_returns_question(tools: dict[str, BaseTool]) -> None:
    result = tools["get_field_question"].invoke(
        {"procedure_code": "2.000635", "field_id": "copies_requested"}
    )
    assert result["question"]


def test_invalid_procedure_code_raises(tools: dict[str, BaseTool]) -> None:
    with pytest.raises(ValueError):
        tools["get_procedure_fee"].invoke({"procedure_code": "9.999999"})
