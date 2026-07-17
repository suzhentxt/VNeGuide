"""Shared contracts, enums, and domain models.

Owner: Người 1. Các module khác phải import model từ đây, không định nghĩa bản sao riêng.
"""

from .contracts import (
    CaseDraft,
    ChatMessage,
    ConversationState,
    ExtractionResult,
    TurnRequest,
    TurnResult,
)
from .enums import (
    FieldType,
    IssueSeverity,
    MessageRole,
    NextAction,
    PackStatus,
    ProcedureCode,
    RuleInputOrigin,
    SourceStatus,
    ValidationStatus,
)
from .models import (
    Approval,
    ChecklistItem,
    FieldDefinition,
    FormDefinition,
    GuidanceStep,
    ProcedurePack,
    RuleContextInput,
    SourceRecord,
    ValidationIssue,
    ValidationResult,
    ValidationRuleDefinition,
)

__all__ = [
    "Approval",
    "CaseDraft",
    "ChatMessage",
    "ChecklistItem",
    "ConversationState",
    "ExtractionResult",
    "FieldDefinition",
    "FieldType",
    "FormDefinition",
    "GuidanceStep",
    "IssueSeverity",
    "MessageRole",
    "NextAction",
    "PackStatus",
    "ProcedureCode",
    "ProcedurePack",
    "RuleContextInput",
    "RuleInputOrigin",
    "SourceRecord",
    "SourceStatus",
    "TurnRequest",
    "TurnResult",
    "ValidationIssue",
    "ValidationResult",
    "ValidationRuleDefinition",
    "ValidationStatus",
]
