from collections import OrderedDict as OD
from typing import Any, TypeVar, Generic, overload, Iterable
from itertools import islice

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
