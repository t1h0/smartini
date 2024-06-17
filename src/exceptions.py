"""smartini-specific exceptions."""


class IniStructureError(Exception):
    """Raised when the ini violates the defined structure."""

    pass


class ContinuationError(IniStructureError):
    """Raised when a continuation violates continuation rules."""

    pass

class DuplicateEntityError(IndentationError):
    """Raised when there are duplicated entities or entities try to be created that
    already exist."""
    pass


class ExtractionError(Exception):
    """Raised when an entity could not be extracted."""

    pass

class EntityNotFound(Exception):
    """Raised when an entity was to be accessed but doesn't exist."""
    pass

class SlotNotFound(Exception):
    """Raised when a slot was to be accessed but doesn't exist."""
    pass    

class SlotAlreadyExists(Exception):
    """Raised when a slot already exists but shouldn't."""
    pass

class UndefinedSectionError(Exception):
    """Raised when an undefined section name is encountered"""

    pass
