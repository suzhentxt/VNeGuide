"""Errors raised while loading or validating the VNeGuide data package."""


class DataPackageError(RuntimeError):
    """Base class for data package failures."""


class DataPackageNotFoundError(DataPackageError):
    """Raised when the repository data directory cannot be discovered."""


class DataFormatError(DataPackageError):
    """Raised when a data file is missing or is not valid JSON."""


class DataIntegrityError(DataPackageError):
    """Raised when cross-file references or invariants are invalid."""


class SchemaValidationError(DataPackageError):
    """Raised when a document does not satisfy its JSON Schema."""

    def __init__(self, violations: tuple[object, ...]) -> None:
        self.violations = violations
        details = "; ".join(str(violation) for violation in violations)
        super().__init__(f"schema validation failed: {details}")
