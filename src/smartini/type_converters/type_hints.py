from typing import get_origin, get_args

from .converters import (
    TypeConverter,
    DEFAULT_BOOL_CONVERTER,
    DEFAULT_GUESS_CONVERTER,
    DEFAULT_LIST_CONVERTER,
    DEFAULT_NUMERIC_CONVERTER,
    DEFAULT_URL_CONVERTER,
    guess_converter,
)

# predefined type hints
type TYPE[*Ts] = str
GUESS = TYPE[DEFAULT_GUESS_CONVERTER]
BOOLEAN = TYPE[DEFAULT_BOOL_CONVERTER]
NUMERIC = TYPE[DEFAULT_NUMERIC_CONVERTER]
URL = TYPE[DEFAULT_URL_CONVERTER]
LIST = TYPE[DEFAULT_LIST_CONVERTER]


def _resolve_TYPE(type_hint: type) -> type[TypeConverter]:

    if not (origin := get_origin(type_hint)) or origin is not TYPE:
        raise ValueError(f"Invalid type hint '{type_hint}'.")

    # get type hints, return first typeconverter
    # or TypeConverter for first type hint != str
    # or guess converter
    args = get_args(type_hint)
    return guess_converter(*args)
