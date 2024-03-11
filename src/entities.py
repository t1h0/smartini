"""Ini entities are either a section name, an option or a comment.
"""

from dataclasses import dataclass

@dataclass
class Comment:
    """An ini comment."""

    content: str
    delimiter: str


class OptionKey(str):
    """An ini option's key."""

    pass


@dataclass
class Option:
    """An ini option."""

    key: OptionKey
    value: str | list[str] | None


class SectionName(str):
    """An ini section's name."""

    pass
