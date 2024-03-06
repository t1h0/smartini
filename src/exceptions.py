class IniStructureError(Exception):
    """Raised when the ini violates the defined structure."""

    pass

class IniContinuationError(IniStructureError):
    """Raised when a continuation violates continuation rules."""
    pass