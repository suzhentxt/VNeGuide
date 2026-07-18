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
    QATopic,
    RuleInputOrigin,
    SourceStatus,
    SuggestionStatus,
    ValidationStatus,
)
from .models import (
    Approval,
    ChecklistItem,
    FieldDefinition,
    FieldSuggestion,
    FormDefinition,
    GuidanceStep,
    JSONValue,
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
    "FieldSuggestion",
    "FieldType",
    "FormDefinition",
    "GuidanceStep",
    "JSONValue",
    "IssueSeverity",
    "MessageRole",
    "NextAction",
    "PackStatus",
    "ProcedureCode",
    "ProcedurePack",
    "QATopic",
    "RuleContextInput",
    "RuleInputOrigin",
    "SourceRecord",
    "SourceStatus",
    "SuggestionStatus",
    "TurnRequest",
    "TurnResult",
    "ValidationIssue",
    "ValidationResult",
    "ValidationRuleDefinition",
    "ValidationStatus",
]
