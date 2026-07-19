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


class QATopic(StrEnum):
    """Reviewed information categories that the extractor may route to Q&A."""

    FEE = "fee"
    PROCESSING_TIME = "processing_time"
    DOCUMENTS = "documents"
    REQUIRED_INFORMATION = "required_information"
    AUTHORITY = "authority"
    CHANNELS = "channels"
    RESULT = "result"
    STEPS = "steps"
    LEGAL_BASIS = "legal_basis"
    CONDITIONS_LIMITED = "conditions_limited"
    FIELD_HELP = "field_help"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class NextAction(StrEnum):
    CONFIRM_PROCEDURE = "confirm_procedure"
    CHOOSE_PORTAL = "choose_portal"
    FILL_MISSING_FIELD = "fill_missing_field"
    REVIEW_SUGGESTION = "review_suggestion"
    UPLOAD_DOCUMENT = "upload_document"
    FIX_VALIDATION = "fix_validation"
    READY_TO_CONTINUE = "ready_to_continue"
    NEEDS_OFFICIAL_REVIEW = "needs_official_review"
    UNSUPPORTED = "unsupported"

    # Python compatibility aliases.  The wire values above are the only values
    # emitted by the refactored conversation core.
    #
    # WARNING: aliases share the same enum member, so ``is`` and ``in`` checks
    # cannot distinguish an alias from its target.  For example
    # ``NextAction.COMPLETE is NextAction.PRESENT_GUIDANCE`` is True, and a
    # ``frozenset({NextAction.PRESENT_GUIDANCE})`` also contains ``COMPLETE``.
    # When a branch must treat aliases differently (e.g. the deep-agent adapter
    # re-composing informational replies but not form-complete turns), use a
    # structural discriminator (state flags, missing fields) rather than the
    # action alone — see ``_is_form_complete`` in ``agent/session_adapter.py``.
    ASK_CLARIFICATION = FILL_MISSING_FIELD
    PRESENT_GUIDANCE = READY_TO_CONTINUE
    VALIDATE_DRAFT = READY_TO_CONTINUE
    REQUEST_CORRECTION = FIX_VALIDATION
    REQUEST_OFFICIAL_REVIEW = NEEDS_OFFICIAL_REVIEW
    COMPLETE = READY_TO_CONTINUE
    OUT_OF_SCOPE = UNSUPPORTED
    CONFIRM_SUGGESTION = REVIEW_SUGGESTION
    MANUAL_INPUT = FILL_MISSING_FIELD
    RETRY = FILL_MISSING_FIELD


class SuggestionStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EDITED = "edited"
