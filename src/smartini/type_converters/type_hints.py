"""types and functions for type hinting type converters."""

from typing import get_origin, get_args

from .converters import (
    TypeConverter,
    DEFAULT_BOOL_CONVERTER,
    DEFAULT_GUESS_CONVERTER,
    DEFAULT_LIST_CONVERTER,
    DEFAULT_NUMERIC_CONVERTER,
    guess_converter,
)

# predefined type hints
type TYPE[*Ts] = str
"""Type annotation for type conversion. First annotated type that the conversion was
successful for will be returned.
"""

GUESS = TYPE[DEFAULT_GUESS_CONVERTER]
"""Type converter that will guess the type."""
BOOL = TYPE[DEFAULT_BOOL_CONVERTER]
"""Boolean type converter."""
NUMERIC = TYPE[DEFAULT_NUMERIC_CONVERTER]
"""Numeric type converter."""
LIST = TYPE[DEFAULT_LIST_CONVERTER]
"""List type converter."""
STR = TYPE[str]
"""Annotation for a string option value."""


def _resolve_TYPE(type_hint: type) -> type[TypeConverter]:
    """Resolve a TYPE type hint to a converter.

    Args:
        type_hint (type): The type hint to resolve.

    Raises:
        ValueError: If type_hint is not TYPE.

    Returns:
        type[TypeConverter]: TypeConverter for the requested type(s).
    """

    if (
        not (origin := get_origin(type_hint)) or origin is not TYPE
    ) and type_hint is not TYPE:
        raise ValueError(f"Invalid type hint '{type_hint}'.")

    # get type hints, and return guess converter based on the type hints
    args = get_args(type_hint)
    return guess_converter(*args)
