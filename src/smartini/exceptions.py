"""smartini-specific exceptions."""


class IniStructureError(Exception):
    """Raised when the ini violates the defined structure."""


class MultilineError(IniStructureError):
    """Raised when a continuation violates continuation rules."""


class DuplicateEntityError(IndentationError):
    """Raised when there are duplicated entities or entities try to be created that
    already exist."""


class ExtractionError(Exception):
    """Raised when an entity could not be extracted."""


class EntityNotFound(Exception):
    """Raised when an entity was to be accessed but doesn't exist."""


class SlotNotFound(Exception):
    """Raised when a slot was to be accessed but doesn't exist."""


class SlotAlreadyExists(Exception):
    """Raised when a slot already exists but shouldn't."""


class UndefinedSectionError(Exception):
    """Raised when an undefined section name is encountered"""
