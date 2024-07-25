"""Converter classes and functions."""

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


class TypeConverter[ConvertedType]:
    """Parent class for type converters. To create a type converter,
    use new_converter()."""

    def __new__(cls, value: Any) -> ConvertedType | Any: ...


def new_converter[
    T
](processor: Callable[[str], T], name: str | None = None) -> type[TypeConverter[T]]:
    """Create a new TypeConverter.

    Args:
        processor (Callable[[str], T]): Callable to process the string input and convert
            it into an instance of arbitrary type. If conversion is not possible, should
            raise exceptions.WrongType.
        name (str | None, optional): Name for the new TypeConverter. Will be appended to
            result into TypeConverter_{name}. If None, will take the processor function's
            name. Defaults to None.

    Returns:
        type[TypeConverter[T]]: TypeConverter that will return the processed input on
            call or the input itself if conversion was not possible.
    """

    def convert(cls, value: Any) -> T | Any:
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

    return type(
        f"TypeConverter_{processor.__name__ if name is None else name}",
        (TypeConverter,),
        {"__new__": convert},
    )


def bool_converter(
    true: str | tuple[str, ...] = ("1", "true", "yes", "y"),
    false: str | tuple[str, ...] = ("0", "false", "no", "n"),
) -> type[TypeConverter[bool]]:
    """Create a new bool converter.

    Args:
        true (str | tuple[str, ...], optional): String(s) that should be regarded as True.
            Defaults to ("1", "true", "yes", "y").
        false (str | tuple[str, ...], optional): String(s) that should be regarded as False.
            Defaults to ("0", "false", "no", "n").

    Returns:
        type[TypeConverter[bool]]: The bool type converter.
    """

    if not isinstance(true, tuple):
        true = (true,)
    true = tuple(i.lower() for i in true)

    if not isinstance(false, tuple):
        false = (false,)
    false = tuple(i.lower() for i in false)

    def to_bool(string: str) -> bool:
        """Converts a string to bool.

        Args:
            string (str): The string to convert.

        Raises:
            WrongType: If conversion was unsuccessful.

        Returns:
            bool: The converted boolean.
        """
        string = string.lower()
        if string in true:
            return True
        elif string in false:
            return False
        raise WrongType

    return new_converter(to_bool)


type Numerics = int | float | complex
"""Possible numeric conversion result types."""


def numeric_converter[
    T: Numerics
](
    numeric_type: type[T] | tuple[type[T], ...] = (int, float, complex),
    decimal_sep: str = ".",
    thousands_sep: str = ",",
) -> type[TypeConverter[T]]:
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
        type[TypeConverter[int | float | complex]]: The numeric type converter.
    """

    if not isinstance(numeric_type, tuple):
        numeric_type = (numeric_type,)

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

    return new_converter(to_num)


@overload
def list_converter[
    T
](
    delimiter: str = ",",
    remove_whitespace: bool = True,
    item_converter: type[TypeConverter[T]] = ...,
) -> type[TypeConverter[list[T | Any]]]: ...
@overload
def list_converter(
    delimiter: str = ",",
    remove_whitespace: bool = True,
    item_converter: None = None,
) -> type[TypeConverter[list[ScalarTypes | Any]]]: ...
def list_converter[
    T
](
    delimiter: str = ",",
    remove_whitespace: bool = True,
    item_converter: type[TypeConverter[T]] | None = None,
) -> type[TypeConverter[list[T | Any] | list[ScalarTypes | Any]]]:
    """Create a new list type converter.

    Args:
        delimiter (str, optional): Delimiter that separates list items. Defaults to ",".
        remove_whitespace (bool, optional): Whether whitespace between items and
            delimiter should be removed. Defaults to True.
        item_converter (type[TypeConverter[Any]]): TypeConverter to convert each list
            item with. If None, will use Guess TypeConverter. Defaults to None.

    Returns:
        type[TypeConverter[list]]: The new list type converter.
    """

    if item_converter is None:
        # guess the items (but no list guess) if no item converter is given
        item_converter = guess_converter(*get_args(ScalarTypes.__value__))

    split_delimiter = (
        rf"\s*{re.escape(delimiter)}\s*" if remove_whitespace else delimiter
    )

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

    return new_converter(to_list)


def guess_converter(
    *types: type[Any | TypeConverter],
) -> type[TypeConverter]:
    """Create a new type converter that guesses the type.

    Args:
        *types (type): The types to guess. If not provided,
            will guess all of ConvertibleTypes.

    Returns:
        type[TypeConverter]: The new Guess-TypeConverter.
    """

    if types:
        # convert the types to guess into type converters
        converters = tuple(_type_hint_to_converter(t) for t in types)  # type: ignore
        # set name for the converter
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
            DEFAULT_NUMERIC_CONVERTER,
            DEFAULT_BOOL_CONVERTER,
            DEFAULT_LIST_CONVERTER,
        )
        name = None

    def guess(string: str) -> Any:
        """Convert to string to a type by guessing.

        Args:
            string (str): The string to convert.

        Raises:
            WrongType: If conversion was unsuccessful.

        Returns:
            Any: The converted type.
        """
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
    T: TypeConverter
](type_hint: type[T],) -> type[T] | None: ...
@overload
def _type_hint_to_converter[
    T: Any
](type_hint: type[T],) -> type[TypeConverter[T]] | None: ...
def _type_hint_to_converter[
    T
](type_hint: type[T],) -> type[TypeConverter[T] | T] | None:
    """Convert a type to its respective TypeConverter.

    Args:
        type_hint (type): The type to convert.

    Returns:
        type[TypeConverter] | None: The matching TypeConvert or None if type is not
            convertible.
    """
    if issubclass(type_hint, TypeConverter):
        return type_hint
    if (origin := get_origin(type_hint)) and origin is list:

        if (list_args := get_args(type_hint)) and len(list_args) == 1:
            # list has exactly one type hint -> get item converter
            item_converter = _type_hint_to_converter(list_args[0])
            return list_converter(item_converter=item_converter)  # type: ignore

        return DEFAULT_LIST_CONVERTER  # type: ignore

    if type_hint in {int, float, complex}:
        return numeric_converter(numeric_type=type_hint)  # type: ignore
    if type_hint is bool:
        return DEFAULT_BOOL_CONVERTER  # type: ignore
    if type_hint is list:
        return DEFAULT_LIST_CONVERTER  # type: ignore
    if type_hint is str:
        return DEFAULT_STRING_CONVERTER  # type: ignore

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
DEFAULT_STRING_CONVERTER = new_converter(lambda x: x, "to_str")
"""String "converter" to save values as they are."""
