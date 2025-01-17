"""Converter classes and functions."""

from functools import wraps
from typing import (
    Callable,
    Any,
    overload,
    get_args,
    get_origin,
)
import re
import contextlib
from .exceptions import WrongType  # leave even if unused

type ScalarTypes = int | float | complex | bool
"""Possible scalar conversion result types."""
type ConvertibleTypes = ScalarTypes | list
"""Possible conversion result types."""


type TypeConverter[ConvertedType] = Callable[[Any], ConvertedType | Any]
"""Type of type converter functions. To create a type converter, use converter decorator."""


def converter[T](processor: Callable[[str], T]) -> TypeConverter[T]:
    """Create a new TypeConverter.

    Args:
        processor (Callable[[str], T]): Callable to process the string input and
            convert it into an instance of arbitrary type. If conversion is not
            possible, should raise exceptions.WrongType.

    Returns:
        TypeConverter[T]: TypeConverter that will return the processed input on call
            or the input itself if conversion was not possible.
    """

    @wraps(processor)
    def convert(value: Any) -> T | Any:
        """Convert value.

        Args:
            value (Any): The value to convert.

        Returns:
            Any: The converted value or the unchanged value if conversion was impossible.
        """
        if isinstance(value, str):
            with contextlib.suppress(WrongType):
                return processor(value)
        return value

    return convert


def string_converter(strip_whitespace: bool = True) -> TypeConverter[str]:
    """Create a new string converter.

    Args:
        strip_whitespace (bool, optional): Whether to strip leading and trailing
            whitespace from the string. Defaults to True.
    """

    @converter
    def to_string(string: str) -> str:
        """Strip string of whitespace.

        Args:
            string (str): The string to strip.

        Returns:
            str: The stripped string.
        """
        if not isinstance(string, str):
            raise WrongType
        return string.strip() if strip_whitespace else string

    return to_string


DEFAULT_STRING_CONVERTER = string_converter()
"""String converter with default conversion parameters."""


def bool_converter(
    true: str | tuple[str, ...] = ("1", "true", "yes", "y"),
    false: str | tuple[str, ...] = ("0", "false", "no", "n"),
) -> TypeConverter[bool]:
    """Create a new bool converter.

    Args:
        true (str | tuple[str, ...], optional): String(s) that should be regarded as True.
            Defaults to ("1", "true", "yes", "y").
        false (str | tuple[str, ...], optional): String(s) that should be regarded as False.
            Defaults to ("0", "false", "no", "n").

    Returns:
        TypeConverter[bool]: The bool converter.
    """

    if not isinstance(true, tuple):
        true = (true,)
    true = tuple(i.lower() for i in true)

    if not isinstance(false, tuple):
        false = (false,)
    false = tuple(i.lower() for i in false)

    @converter
    def to_bool(string: str) -> bool:
        """Converts a string to bool.

        Args:
            string (str): The string to convert.

        Raises:
            WrongType: If conversion was unsuccessful.

        Returns:
            bool: The converted boolean.
        """
        string = string.lower().strip()
        if string in true:
            return True
        elif string in false:
            return False
        raise WrongType

    return to_bool


type Numerics = int | float | complex
"""Possible numeric conversion result types."""


def numeric_converter[
    T: Numerics
](
    numeric_type: type[T] | tuple[type[T], ...] = (int, float, complex),
    decimal_sep: str = ".",
    thousands_sep: str = ",",
) -> TypeConverter[T]:
    """Create a new numeric type converter.

    Args:
        numeric_type (type[Numerics] | tuple[type[Numerics], ...], optional): The type
            to convert to. If multiple are given, the type converter will return the
            first type that the conversion was successful for.
            Defaults to (int, float, complex).
        decimal_sep (str, optional): Possible decimal separator inside the string.
            Defaults to ".".
        thousands_sep (str, optional): Possible thousands separator inside the string.
            Defaults to ",".

    Returns:
        TypeConverter[int | float | complex]: The numeric type converter.
    """

    if not isinstance(numeric_type, tuple):
        numeric_type = (numeric_type,)

    @converter
    def to_num(string: str) -> T:
        """Convert string to numeric type.

        Args:
            string (str): The string to convert.

        Raises:
            WrongType: If conversion was unsuccessful.

        Returns:
            Numerics: Converted string.
        """
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
        # remove whitespaces
        string = string.replace(" ", "")
        for converter in numeric_type:
            with contextlib.suppress(ValueError):
                return converter(string)
        raise WrongType

    return to_num


@overload
def list_converter[
    T
](
    delimiter: str = ",",
    remove_whitespace: bool = True,
    item_converter: TypeConverter[T] = ...,
) -> TypeConverter[list[T | Any]]: ...
@overload
def list_converter(
    delimiter: str = ",",
    remove_whitespace: bool = True,
    item_converter: None = None,
) -> TypeConverter[list[ScalarTypes | Any]]: ...
def list_converter[
    T
](
    delimiter: str = ",",
    remove_whitespace: bool = True,
    item_converter: TypeConverter[T] | None = None,
) -> TypeConverter[list[T | Any] | list[ScalarTypes | Any]]:
    """Create a new list type converter.

    Args:
        delimiter (str, optional): Delimiter that separates list items. Defaults to ",".
        remove_whitespace (bool, optional): Whether whitespace between items and
            delimiter should be removed. Defaults to True.
        item_converter (TypeConverter[Any]): TypeConverter to convert each list
            item with. If None, will use Guess TypeConverter. Defaults to None.

    Returns:
        TypeConverter[list]: The new list type converter.
    """

    if item_converter is None:
        # guess the items (but no list guess) if no item converter is given
        item_converter = guess_converter(*get_args(ScalarTypes.__value__))

    split_delimiter = (
        rf"\s*{re.escape(delimiter)}\s*" if remove_whitespace else delimiter
    )

    @converter
    def to_list(string: str) -> list[T | str] | list[ScalarTypes | str]:
        """Convert a string to a list.

        Args:
            string (str): The string to convert.

        Raises:
            WrongType: If conversion was unsuccessful.

        Returns:
            list: Converted list.
        """
        if delimiter not in string:
            raise WrongType
        return [
            item_converter(s) for s in re.split(pattern=split_delimiter, string=string)
        ]

    return to_list


def guess_converter(
    *types: type[Any] | TypeConverter,
    fallback: TypeConverter = DEFAULT_STRING_CONVERTER,
) -> TypeConverter:
    """Create a new type converter that guesses the type.

    Args:
        *types (type): The types to guess. If not provided,
            will guess all of ConvertibleTypes.
        fallback (TypeConverter, optional): Fallback converter if no type
            could be guessed.

    Returns:
        TypeConverter: The new Guess-TypeConverter.
    """

    if types:
        # convert the types to guess into type converters
        converters = tuple(_type_hint_to_converter(t) for t in types)
    else:
        converters = (
            DEFAULT_NUMERIC_CONVERTER,
            DEFAULT_BOOL_CONVERTER,
            DEFAULT_LIST_CONVERTER,
        )

    @converter
    def guess(string: str) -> Any:
        """Convert to string to a type by guessing.

        Args:
            string (str): The string to convert.

        Raises:
            WrongType: If conversion was unsuccessful.

        Returns:
            Any: The converted type.
        """
        for conv in converters:
            if conv is not None and (guess := conv(string)) != string:
                return guess
        return fallback(string)

    return guess


@overload
def _type_hint_to_converter[
    T: ConvertibleTypes
](type_hint: type[T],) -> TypeConverter[T]: ...
@overload
def _type_hint_to_converter[
    T: Any
](type_hint: TypeConverter[T],) -> TypeConverter[T]: ...
def _type_hint_to_converter[
    T
](type_hint: Any,) -> TypeConverter[T] | None:
    """Convert a type to its respective TypeConverter.

    Args:
        type_hint (type): The type to convert.

    Returns:
        TypeConverter | None: The matching TypeConvert or None if type is not
            convertible.
    """
    if (origin := get_origin(type_hint)) and origin is list:

        if (list_args := get_args(type_hint)) and len(list_args) == 1:
            # list has exactly one type hint -> get item converter
            item_converter = _type_hint_to_converter(list_args[0])
            return list_converter(item_converter=item_converter)

        return DEFAULT_LIST_CONVERTER

    if type_hint in {int, float, complex}:
        return numeric_converter(numeric_type=type_hint)
    if type_hint is bool:
        return DEFAULT_BOOL_CONVERTER
    if type_hint is list:
        return DEFAULT_LIST_CONVERTER
    if type_hint is str:
        return DEFAULT_STRING_CONVERTER
    if isinstance(type_hint, Callable):
        return type_hint

    return None


# default converters
DEFAULT_BOOL_CONVERTER = bool_converter()
"""Bool converter with default conversion parameters."""
DEFAULT_NUMERIC_CONVERTER = numeric_converter()
"""Numeric converter with default conversion parameters."""
DEFAULT_LIST_CONVERTER = list_converter()
"""List converter with default conversion parameters."""
DEFAULT_GUESS_CONVERTER = guess_converter()
"""Guess converter with default conversion parameters."""
