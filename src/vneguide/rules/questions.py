"""Deterministic next-question selection."""

from __future__ import annotations

from vneguide.data import ProcedureRepository
from vneguide.domain import ProcedureCode


class QuestionSelector:
    def __init__(self, repository: ProcedureRepository) -> None:
        self._repository = repository

    def question_for(self, procedure_code: ProcedureCode | str, field_id: str) -> str:
        for field in self._repository.fields_for(procedure_code):
            if field.field_id == field_id:
                return f"Vui lòng cho biết {field.label.lower()}."
        return f"Vui lòng bổ sung thông tin cho trường {field_id}."
