import re
from collections import OrderedDict as OD
from typing import Any, TypeVar, Generic, overload, Iterable, Callable
from itertools import islice
from .globals import INTERNAL_PREFIX, VARIABLE_PREFIX


def _str_to_var(string: str) -> str:
    """Convert a string to a valid python variable name.

    Args:
        string (str): The string to convert.

    Returns:
        str: The valid variable name.
    """
    return re.sub(
        rf"^(?=\d|{INTERNAL_PREFIX})", VARIABLE_PREFIX, re.sub(r"\W", "_", string)
    )


def copy_doc[
    **P, T
](doc_source: Callable[P, T], annotations: bool = False) -> Callable[
    [Callable[P, T]], Callable[P, T]
]:
    """Decorator to copy the docstring of doc_source to another.
    Inspired by Trevor (stackoverflow.com/users/13905088/trevor)
    from: stackoverflow.com/questions/68901049/
        copying-the-docstring-of-function-onto-another-function-by-name

    Args:
        doc_source (Callable): The source function to copy the docstring from.
        annotations (bool, optional): Whether to also copy annotations. Defaults to False.

    Returns:
        Callable: The decorated function.

    """

    def wrapped(doc_target: Callable[P, T]) -> Callable[P, T]:
        doc_target.__doc__ = doc_source.__doc__
        if annotations:
            doc_target.__annotations__ = doc_source.__annotations__
        return doc_target

    return wrapped


### Ordered Dict with ILoc functionality

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


class OrderedDict(OD[_KT, _VT]):
    """OrderedDict with iLoc functionality."""

    def __init__(self, *args, **kwargs) -> None:
        self.iloc: _iLocIndexer[_KT, _VT] = _iLocIndexer(self)
        super().__init__(*args, **kwargs)


class _iLocIndexer(Generic[_KT, _VT]):

    def __init__(self, target: OrderedDict[_KT, _VT]) -> None:
        self.target = target

    @overload
    def __getitem__(self, key: int) -> tuple[_KT, _VT]: ...

    @overload
    def __getitem__(self, key: list[int] | slice) -> list[tuple[_KT, _VT]]: ...

    def __getitem__(
        self, key: int | list[int] | slice
    ) -> list[tuple[_KT, _VT]] | tuple[_KT, _VT]:

        dict_len = len(self.target)

        # convert negative indices to positive indices
        if isinstance(key, (int, list)):
            keys = [key] if isinstance(key, int) else key
            items = tuple(self.target.items())
            iterator = (items[dict_len + val if val < 0 else val] for val in keys)
        elif isinstance(key, slice):
            _slice = [
                dict_len + s if s is not None and s < 0 else s
                for s in (key.start, key.stop, key.step)
            ]
            iterator = islice(self.target.items(), *_slice)
        else:
            raise TypeError("key must be of type int, list or slice.")

        try:
            if result := list(iterator):
                return result[0] if isinstance(key, int) else result
            raise IndexError
        except (StopIteration, IndexError):
            raise IndexError("OrderedDict index out of range")

    def __setitem__(self, key: int | list[int] | slice, value: Any) -> None:
        if isinstance(key, (list, slice)):
            if not isinstance(value, Iterable):
                raise TypeError("Can only assign an iterable.")
        elif isinstance(key, int):
            key = [key]
            value = [value]
        else:
            raise TypeError("key must be of type int, list or slice.")

        for (k, _), val in zip(self[key], value):
            self.target[k] = val
