from typing import (
    Callable,
    TypeVar,
    Any,
)
import re
import contextlib
from urllib import parse as urlparse
from .exceptions import WrongType

T = TypeVar("T")


class TypeConverter[ConvertedType]:
    """Parent class for TypeConverters."""

    def __new__(cls, value: Any) -> ConvertedType | Any: ...


def new_converter(processor: Callable[[str], T]) -> type[TypeConverter[T]]:

    TC = TypeConverter[T]

    class _TypeConverter(TC):
        def __new__(cls, value: Any) -> T | Any:
            if isinstance(value, str):
                with contextlib.suppress(WrongType):
                    return processor(value)
            return value

    return _TypeConverter


def bool_converter(
    true: str | tuple[str, ...] = ("1", "true", "yes", "y"),
    false: str | tuple[str, ...] = ("0", "false", "no", "n"),
) -> type[TypeConverter[bool]]:

    if not isinstance(true, tuple):
        true = (true,)
    true = tuple(i.lower() for i in true)

    if not isinstance(false, tuple):
        false = (false,)
    false = tuple(i.lower() for i in false)

    def str_to_bool(string: str) -> bool:
        string = string.lower()
        if string in true:
            return True
        elif string in false:
            return False
        raise WrongType

    return new_converter(str_to_bool)


def list_converter(
    delimiter: str = ",",
    ignore_whitespace: bool = True,
    item_valtype: Callable[[str], T] = str,
) -> type[TypeConverter[list[T]]]:

    split_delimiter = (
        rf"\s*{re.escape(delimiter)}\s*" if ignore_whitespace else delimiter
    )

    def str_to_list(string: str) -> list[T]:
        if delimiter not in string:
            raise WrongType
        return [
            item_valtype(s) for s in re.split(pattern=split_delimiter, string=string)
        ]

    return new_converter(str_to_list)


def numeric_converter(
    decimal_sep: str = ".", thousands_sep: str = ","
) -> type[TypeConverter[int | float | complex]]:
    def str_to_num(string: str) -> int | float | complex:
        string = string.replace(decimal_sep, ".").replace(thousands_sep, "")
        for converter in (int, float, complex):
            with contextlib.suppress(ValueError):
                return converter(string)
        raise WrongType

    return new_converter(str_to_num)


def url_converter() -> type[TypeConverter[urlparse.ParseResult]]:

    def str_to_url(string: str) -> urlparse.ParseResult:
        if (url := urlparse.urlparse(string)).hostname:
            return url
        raise WrongType

    return new_converter(str_to_url)


type guess_types = int | float | complex | str | urlparse.ParseResult
type recursive_guess = list[guess_types | recursive_guess]


def guess_converter() -> type[TypeConverter[guess_types | recursive_guess]]:

    def guess(string: str) -> guess_types | recursive_guess:
        if (bool_guess := bool_converter(true="true", false="false")(string)) != string:
            return bool_guess
        if (numeric_guess := numeric_converter()(string)) != string:
            return numeric_guess
        if (url_guess := url_converter()(string)) != string:
            return url_guess
        if (list_guess := list_converter()(string)) != string:
            return [guess(item) for item in list_guess]
        return string

    return new_converter(guess)


DEFAULT_GUESS_CONVERTER = guess_converter()
DEFAULT_LIST_CONVERTER = list_converter()
DEFAULT_NUMERIC_CONVERTER = numeric_converter()
DEFAULT_BOOL_CONVERTER = bool_converter()
