from typing import Union
from .converters import guess_converter, bool_converter, numeric_converter

GUESS = Union[str, guess_converter()]
BOOLEAN = Union[str, bool_converter()]
NUMERIC = Union[str, numeric_converter()]
