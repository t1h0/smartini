"""smartini-specific exceptions and warnings"""

# ---------- #
# Exceptions
# ---------- #


class DuplicateEntityError(IndentationError):
    """Raised when entities are tried to be created that already exist."""


class ExtractionError(Exception):
    """Raised when an entity could not be extracted."""


class EntityNotFound(Exception):
    """Raised when an entity was to be accessed but doesn't exist."""


class SlotNotFound(Exception):
    """Raised when a slot was to be accessed but doesn't exist."""


class SlotAlreadyExists(Exception):
    """Raised when a slot already exists but shouldn't."""


# ---------- #
# Warnings
# ---------- #


class IniStructureWarning(Warning):
    """Raised when the ini violates the defined structure."""


class UndefinedEntityWarning(IniStructureWarning):
    """Raised when undefined entity is encountered but undefined entities of that type are being ignored."""


class UndefinedSectionWarning(UndefinedEntityWarning):
    """Raised when an undefined section is encountered but undefined sections are being ignored."""


class UndefinedOptionWarning(UndefinedEntityWarning):
    """Raised when an undefined option is encountered but undefined options are being ignored."""


class MultilineWarning(IniStructureWarning):
    """Raised when a continuation violates continuation rules."""
