from collections import OrderedDict as OD
from typing import Any, TypeVar
from itertools import islice

_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


class OrderedDict(OD[_KT, _VT]):

    def __init__(self, *args, **kwargs) -> None:
        self.iloc = _iLocIndexer(self)
        super().__init__(*args, **kwargs)


class _iLocIndexer:

    def __init__(self, ordered_dict: OrderedDict) -> None:
        self.ordered_dict = ordered_dict

    def __getitem__(self, key: int) -> tuple[Any, Any]:
        iterator = self.ordered_dict.items()

        if key < 0:
            iterator = reversed(iterator)
            key = abs(key) - 1

        value = next(islice(iterator, key, None), None)
        if not value:
            raise IndexError("OrderedDict index out of range")
        return value
