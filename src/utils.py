from src.globals import INTERNAL_PREFIX, VARIABLE_PREFIX
import re


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
