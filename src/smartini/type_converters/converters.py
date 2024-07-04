from typing import (
    Callable,
    Any,
    overload,
    get_args,
    get_origin,
)
import re
import contextlib
from urllib import parse as urlparse
from .exceptions import WrongType

type ScalarTypes = int | float | complex | bool | urlparse.ParseResult


class TypeConverter[ConvertedType]:
    """Parent class for TypeConverters."""

    def __new__(cls, value: Any) -> ConvertedType | Any: ...


def new_converter[
    T
](processor: Callable[[str], T], name: str | None = None) -> type[TypeConverter[T]]:

    def converter(cls, value: Any) -> T | Any:
        if isinstance(value, str):
            with contextlib.suppress(WrongType):
                return processor(value)
        return value

    return type(
        f"TypeConverter_{processor.__name__ if name is None else name}",
        (TypeConverter,),
        {"__new__": converter},
    )


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

    def to_bool(string: str) -> bool:
        string = string.lower()
        if string in true:
            return True
        elif string in false:
            return False
        raise WrongType

    return new_converter(to_bool)


type Numerics = int | float | complex


def numeric_converter[
    T: Numerics
](
    numeric_type: type[T] | tuple[type[T], ...] = (int, float, complex),
    decimal_sep: str = ".",
    thousands_sep: str = ",",
) -> type[TypeConverter[T]]:

    if not isinstance(numeric_type, tuple):
        numeric_type = (numeric_type,)

    def to_num(string: str) -> T:
        if thousands_sep in string:
            ts = re.escape(thousands_sep)
            # assure that thousands separator is actually separating thousands
            if any(
                len(dec) != 3 for dec in re.findall(rf"(?<={ts})\d+(?={ts}|$)", string)
            ):
                raise WrongType
            string = string.replace(thousands_sep, "")
        if decimal_sep in string:
            ds = re.escape(decimal_sep)
            # assure decimal separator is actually separating the decimal
            if not re.fullmatch(rf"(?=.*{ds})(?!.*{ds}.*{ds}).*", string):
                raise WrongType
            string = string.replace(decimal_sep, ".")
        for converter in numeric_type:
            with contextlib.suppress(ValueError):
                return converter(string)
        raise WrongType

    return new_converter(to_num)


def url_converter() -> type[TypeConverter[urlparse.ParseResult]]:

    def to_url(string: str) -> urlparse.ParseResult:
        if (url := urlparse.urlparse(string)).hostname:
            return url
        raise WrongType

    return new_converter(to_url)


@overload
def list_converter[
    T
](
    delimiter: str = ",",
    ignore_whitespace: bool = True,
    item_converter: type[TypeConverter[T]] = ...,
) -> type[TypeConverter[list[T | Any]]]: ...
@overload
def list_converter[
    T
](
    delimiter: str = ",",
    ignore_whitespace: bool = True,
    item_converter: None = None,
) -> type[TypeConverter[list[ScalarTypes | Any]]]: ...
def list_converter[
    T
](
    delimiter: str = ",",
    ignore_whitespace: bool = True,
    item_converter: type[TypeConverter[T]] | None = None,
) -> type[TypeConverter[list[T | Any] | list[ScalarTypes | Any]]]:

    if item_converter is None:
        item_converter = guess_converter(*get_args(ScalarTypes.__value__))

    split_delimiter = (
        rf"\s*{re.escape(delimiter)}\s*" if ignore_whitespace else delimiter
    )

    def to_list(string: str) -> list[T | str] | list[ScalarTypes | str]:
        if delimiter not in string:
            raise WrongType
        return [
            item_converter(s) for s in re.split(pattern=split_delimiter, string=string)
        ]

    return new_converter(to_list)


def guess_converter(
    *types: type,
) -> type[TypeConverter]:

    if types:
        converters = tuple(
            t if issubclass(t, TypeConverter) else _type_hint_to_converter(t)
            for t in types
        )
        name = "guess_" + "_".join(
            (
                postfix[0]
                if (
                    postfix := re.search(
                        r"(?<=_).*", cname := c.__name__ if c else "None"
                    )
                )
                else cname
            )
            for c in converters
        )
    else:
        converters = (
            DEFAULT_BOOL_CONVERTER,
            DEFAULT_NUMERIC_CONVERTER,
            DEFAULT_URL_CONVERTER,
            DEFAULT_LIST_CONVERTER,
        )
        name = None

    def guess(string: str) -> Any:
        for converter in converters:
            if converter is not None and (guess := converter(string)) != string:
                return guess
        raise WrongType

    return new_converter(processor=guess, name=name)


@overload
def _type_hint_to_converter[
    T: ScalarTypes
](type_hint: type[T],) -> type[TypeConverter[T]]: ...
@overload
def _type_hint_to_converter[
    T: Any
](type_hint: type[T],) -> type[TypeConverter[T]] | None: ...
def _type_hint_to_converter[
    T
](type_hint: type[T],) -> type[TypeConverter[T]] | None:

    if origin := get_origin(type_hint):

        if origin is list:

            if (list_args := get_args(type_hint)) and len(list_args) == 1:
                # list has exactly one type hint -> get item converter
                item_converter = _type_hint_to_converter(list_args[0])
                return list_converter(item_converter=item_converter)

            return DEFAULT_LIST_CONVERTER

        else:
            raise ValueError(f"Invalid type hint '{type_hint}'.")

    if type_hint in {int, float, complex}:
        return numeric_converter(numeric_type=type_hint)
    if type_hint is bool:
        return DEFAULT_BOOL_CONVERTER
    if type_hint is list:
        return DEFAULT_LIST_CONVERTER
    if type_hint is urlparse.ParseResult:
        return DEFAULT_URL_CONVERTER

    return None


DEFAULT_BOOL_CONVERTER = bool_converter()
DEFAULT_NUMERIC_CONVERTER = numeric_converter()
DEFAULT_URL_CONVERTER = url_converter()
DEFAULT_LIST_CONVERTER = list_converter()
DEFAULT_GUESS_CONVERTER = guess_converter()
