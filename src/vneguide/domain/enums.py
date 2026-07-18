"""Stable enums shared by every VNeGuide module."""

from enum import StrEnum


class ProcedureCode(StrEnum):
    """Procedure codes approved for the current MVP data package."""

    BIRTH_CERTIFICATE_COPY = "2.000635"
    HOUSING_CONDITION_CONFIRMATION = "1.013314"
    TEMPORARY_RESIDENCE_REGISTRATION = "1.004194"


class PackStatus(StrEnum):
    DRAFT = "draft"
    NEEDS_REVIEW = "needs_review"
    APPROVED = "approved"
    STALE = "stale"
    RETIRED = "retired"


class ValidationStatus(StrEnum):
    READY_TO_SUBMIT = "ready_to_submit"
    NEEDS_CORRECTION = "needs_correction"
    NEEDS_OFFICIAL_REVIEW = "needs_official_review"
    OUT_OF_SCOPE = "out_of_scope"


class IssueSeverity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    NEEDS_REVIEW = "needs_review"
    INFO = "info"


class FieldType(StrEnum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    ENUM = "enum"


class SourceStatus(StrEnum):
    APPROVED = "approved"
    CONTEXT_ONLY = "context_only"
    DISCOVERY_ONLY = "discovery_only"


class RuleInputOrigin(StrEnum):
    INTENT_EXTRACTION = "intent_extraction"
    DOCUMENT_CHECK = "document_check"
    USER_DECLARATION = "user_declaration"
    DERIVED = "derived"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class NextAction(StrEnum):
    ASK_CLARIFICATION = "ask_clarification"
    PRESENT_GUIDANCE = "present_guidance"
    VALIDATE_DRAFT = "validate_draft"
    REQUEST_CORRECTION = "request_correction"
    REQUEST_OFFICIAL_REVIEW = "request_official_review"
    COMPLETE = "complete"
    OUT_OF_SCOPE = "out_of_scope"
    CONFIRM_PROCEDURE = "confirm_procedure"
    CONFIRM_SUGGESTION = "confirm_suggestion"
    MANUAL_INPUT = "manual_input"
    RETRY = "retry"


class SuggestionStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"
