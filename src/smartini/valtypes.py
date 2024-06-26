from typing import (
    Callable,
    Union,
    get_type_hints,
    get_args,
    Literal,
    Any,
    TypeVar,
    overload,
)
import re
import contextlib

T = TypeVar("T")


class WrongValType(Exception):
    """Raised when a value could not be resolved to its annotated ValType."""

    pass


class ValType[ConvertedType]:
    """Parent class for ValTypes."""

    def __new__(cls, string: str) -> ConvertedType: ...


@overload
def new_valtype(
    processor: Callable[[str], T],
    fail_action: Literal["exception"] | None = "exception",
) -> type[ValType[T]]: ...
@overload
def new_valtype(
    processor: Callable[[str], T], fail_action: type[str] = ...
) -> type[ValType[T | str]]: ...
def new_valtype(
    processor: Callable[[str], T],
    fail_action: Literal["exception"] | None | type[str] = "exception",
) -> type[ValType[T | None | str]]:

    VT = ValType[T | None | str]

    class _ValType(VT):
        def __new__(cls, string: str) -> T | None | str:
            processed = processor(string)
            if processed is None:
                match fail_action:
                    case "exception":
                        raise WrongValType(
                            f"'{string}' could not be resolved to annotated ValType."
                        )
                    case None:
                        return None
                    case str:
                        return string
            return processed

    return _ValType


def bool_type(
    true_aliases: tuple[str, ...] = ("1", "true", "yes"),
    false_aliases: tuple[str, ...] = ("0", "false", "no"),
) -> type[ValType[bool | None]]:
    true_aliases = tuple(i.lower() for i in true_aliases)
    false_aliases = tuple(i.lower() for i in false_aliases)

    def str_to_bool(string: str) -> bool | None:
        string = string.lower()
        if string in true_aliases:
            return True
        if string in false_aliases:
            return False
        return None

    return new_valtype(str_to_bool, fail_action=None)


def list_type(
    delimiter: str = ",",
    ignore_whitespace: bool = True,
    item_valtype: Callable[[str], T] = str,
) -> type[ValType[list[T] | None]]:

    split_delimiter = (
        rf"\s*{re.escape(delimiter)}\s*" if ignore_whitespace else delimiter
    )

    def str_to_list(string: str) -> list[T] | None:
        if delimiter not in string:
            return None
        return [
            item_valtype(s) for s in re.split(pattern=split_delimiter, string=string)
        ]

    return new_valtype(str_to_list, fail_action=None)


def numeric_type(
    decimal_sep: str = ".", thousands_sep: str = ","
) -> type[ValType[int | float | complex | None]]:
    def str_to_num(string: str) -> int | float | complex | None:
        string = string.replace(decimal_sep, ".").replace(thousands_sep, "")
        for converter in (int, float, complex):
            with contextlib.suppress(ValueError):
                return converter(string)
        return None

    return new_valtype(str_to_num, fail_action=None)


type guess_types = int | float | complex | str
type recursive_guess = list[guess_types | recursive_guess]


def guess_type() -> type[ValType[guess_types | recursive_guess]]:

    def guess(string: str) -> guess_types | recursive_guess:
        if (list_guess := list_type()(string)) is not None:
            return [guess(item) for item in list_guess]
        if (bool_guess := bool_type()(string)) is not None:
            return bool_guess
        if (num_guess := numeric_type()(string)) is not None:
            return num_guess
        return string

    return new_valtype(guess)


GUESS = Union[str, guess_type()]
BOOLEAN = Union[str, bool_type()]
NUMERIC = Union[str, numeric_type()]
