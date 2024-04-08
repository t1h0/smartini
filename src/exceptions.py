"""smartini-specific exceptions."""


class IniStructureError(Exception):
    """Raised when the ini violates the defined structure."""

    pass


class ContinuationError(IniStructureError):
    """Raised when a continuation violates continuation rules."""

    pass


class ExtractionError(Exception):
    """Raised when an entity could not be extracted."""

    pass


class UndefinedSectionError(Exception):
    """Raised when an undefined section name is encountered"""

    pass
