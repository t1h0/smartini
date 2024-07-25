from typing import Literal

INTERNAL_PREFIX = "_"
INTERNAL_PREFIX_IN_WORDS = "underscores"
SECTION_NAME_VARIABLE = f"{INTERNAL_PREFIX}name"
COMMENT_VAR_PREFIX = f"{INTERNAL_PREFIX}COMMENT_"
UNNAMED_SECTION_NAME = f"{INTERNAL_PREFIX}UNNAMED"
VARIABLE_PREFIX = "s_"  # for generated variables
VALID_MARKERS = Literal[
    "\\",
    "!",
    '"',
    "§",
    "%",
    "&",
    "/",
    "(",
    ")",
    "?",
    ":",
    ";",
    "#",
    "'",
    "*",
    ">",
    "<",
    "=",
]
"""Valid characters for markers (option delimiter, comment prefix or multiline prefix)."""
