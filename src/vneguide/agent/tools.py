"""Grounded fact-retrieval tools for the deep-agent layer.

Every tool wraps the reviewed data layer (:class:`ProcedureQAResponder`,
:class:`RuleEngine`, :class:`ProcedureRepository`, :class:`QuestionSelector`)
and returns reviewed data plus ``source_ids``. The LLM cannot author facts —
tools only retrieve. This is the safe mechanism for relaxing AGENTS.md: the
LLM is proactive (it chooses which tool to call) but every fact is traceable
to a reviewed ``source_id``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from langchain_core.tools import tool
from langchain_core.tools.base import BaseTool

from ..ai.schemas import InformationRequest
from ..data import ProcedureRepository
from ..domain import QATopic
from ..rules import ProcedureQAResponder, QAAnswer, QuestionSelector, RuleEngine


@dataclass(frozen=True, slots=True)
class ToolContext:
    """Dependencies injected into every tool via closure."""

    repository: ProcedureRepository
    qa_responder: ProcedureQAResponder
    rule_engine: RuleEngine
    question_selector: QuestionSelector


def build_tools(ctx: ToolContext) -> list[BaseTool]:
    """Build the list of grounded fact-retrieval tools bound to ``ctx``."""

    def _qa_answer(
        code: str, topic: QATopic, *, target_field_id: str | None = None
    ) -> dict[str, Any]:
        request = InformationRequest(
            topics=(topic,),
            target_field_id=target_field_id,
        )
        answer: QAAnswer = ctx.qa_responder.answer(code, request)
        return {"text": answer.text, "source_ids": list(answer.source_ids)}

    @tool
    def get_procedure_fee(procedure_code: str) -> dict[str, Any]:
        """Lấy lệ phí của thủ tục từ data package đã review."""
        return _qa_answer(procedure_code, QATopic.FEE)

    @tool
    def get_processing_time(procedure_code: str) -> dict[str, Any]:
        """Lấy thời hạn xử lý của thủ tục từ data package đã review."""
        return _qa_answer(procedure_code, QATopic.PROCESSING_TIME)

    @tool
    def get_required_documents(procedure_code: str) -> dict[str, Any]:
        """Lấy danh sách tài liệu bắt buộc của thủ tục từ data package đã review."""
        return _qa_answer(procedure_code, QATopic.DOCUMENTS)

    @tool
    def get_required_information(procedure_code: str) -> dict[str, Any]:
        """Lấy thông tin công dân cần cung cấp cho thủ tục từ data package đã review."""
        return _qa_answer(procedure_code, QATopic.REQUIRED_INFORMATION)

    @tool
    def get_authority(procedure_code: str) -> dict[str, Any]:
        """Lấy cơ quan có thẩm quyền của thủ tục từ data package đã review."""
        return _qa_answer(procedure_code, QATopic.AUTHORITY)

    @tool
    def get_submission_channels(procedure_code: str) -> dict[str, Any]:
        """Lấy kênh nộp hồ sơ của thủ tục từ data package đã review."""
        return _qa_answer(procedure_code, QATopic.CHANNELS)

    @tool
    def get_result(procedure_code: str) -> dict[str, Any]:
        """Lấy kết quả của thủ tục từ data package đã review."""
        return _qa_answer(procedure_code, QATopic.RESULT)

    @tool
    def get_guidance_steps(procedure_code: str) -> dict[str, Any]:
        """Lấy trình tự thực hiện thủ tục từ data package đã review."""
        return _qa_answer(procedure_code, QATopic.STEPS)

    @tool
    def get_legal_basis(procedure_code: str) -> dict[str, Any]:
        """Lấy căn cứ pháp lý của thủ tục từ data package đã review."""
        return _qa_answer(procedure_code, QATopic.LEGAL_BASIS)

    @tool
    def get_conditions_and_limits(procedure_code: str) -> dict[str, Any]:
        """Lấy điều kiện và phạm vi áp dụng của thủ tục từ data package đã review."""
        return _qa_answer(procedure_code, QATopic.CONDITIONS_LIMITED)

    @tool
    def get_field_help(procedure_code: str, field_id: str) -> dict[str, Any]:
        """Lấy hướng dẫn điền một mục (field) của thủ tục từ data package đã review."""
        return _qa_answer(procedure_code, QATopic.FIELD_HELP, target_field_id=field_id)

    @tool
    def get_missing_fields(procedure_code: str, draft_values: dict[str, Any]) -> dict[str, Any]:
        """Lấy danh sách field còn thiếu trong hồ sơ hiện tại."""
        missing = ctx.rule_engine.missing_fields(procedure_code, draft_values)
        return {"missing_field_ids": list(missing)}

    @tool
    def validate_draft(
        procedure_code: str,
        draft_values: dict[str, Any],
    ) -> dict[str, Any]:
        """Kiểm tra hồ sơ hiện tại xem đã hợp lệ chưa."""
        result = ctx.rule_engine.validate(procedure_code, draft_values)
        return {
            "status": result.status.value,
            "readiness_score": result.readiness_score,
            "issues": [
                {
                    "rule_id": issue.rule_id,
                    "severity": issue.severity.value,
                    "message": issue.message,
                    "field_id": issue.field_id,
                    "suggestion": issue.suggestion,
                    "source_ids": list(issue.source_ids),
                }
                for issue in result.issues
            ],
            "source_ids": list(result.source_ids),
        }

    @tool
    def get_field_question(procedure_code: str, field_id: str) -> dict[str, Any]:
        """Lấy câu hỏi gợi ý cho một field của thủ tục."""
        question = ctx.question_selector.question_for(procedure_code, field_id)
        return {"question": question}

    @tool
    def list_procedures() -> dict[str, Any]:
        """Liệt kê 3 thủ tục VNeGuide hỗ trợ."""
        packs = ctx.repository.list_procedures()
        return {
            "procedures": [
                {
                    "code": pack.procedure_code,
                    "name": pack.procedure_name,
                }
                for pack in packs
            ]
        }

    return [
        get_procedure_fee,
        get_processing_time,
        get_required_documents,
        get_required_information,
        get_authority,
        get_submission_channels,
        get_result,
        get_guidance_steps,
        get_legal_basis,
        get_conditions_and_limits,
        get_field_help,
        get_missing_fields,
        validate_draft,
        get_field_question,
        list_procedures,
    ]


__all__ = ["ToolContext", "build_tools"]
