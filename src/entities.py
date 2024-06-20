"""Ini entities are either a section name, an option or a comment."""

from typing import overload, Any, Self, TypeVar
import re
from src.exceptions import ExtractionError
from src.slots import SlotAccess, SlotEntity

T = TypeVar("T")


class Comment:
    """An ini comment."""

    @overload
    def __init__(
        self,
        content_without_prefix: str = ...,
        prefix: ... = ...,
        content_with_prefix: None = ...,
    ) -> None: ...
    @overload
    def __init__(
        self,
        content_without_prefix: None = ...,
        prefix: str | re.Pattern | tuple[str | re.Pattern, ...] = ...,
        content_with_prefix: str = ...,
    ) -> None: ...

    def __init__(
        self,
        content_without_prefix: str | None = None,
        prefix: str | re.Pattern | tuple[str | re.Pattern, ...] | None = None,
        content_with_prefix: str | None = None,
    ) -> None:
        """An ini comment.

        Args:
            content_without_prefix (str | None, optional): Content with prefix removed.
                Should be None if content_with_prefix is provided, otherwise the latter
                will be ignored. Defaults to None.
            prefix (str | re.Pattern | tuple[str | re.Pattern, ...] | None, optional):
                One or more prefixes that can denote the comment
                (used for content_with_prefix). Defaults to None.
            content_with_prefix (str | None, optional): Content including prefix.
                Will be ignored if content_without_prefix is provided. Defaults to None.
        """
        if not isinstance(prefix, tuple):
            prefix = (prefix if prefix is not None else "",)
        assert isinstance(prefix, tuple)

        if content_without_prefix is not None:
            self.content = content_without_prefix
            return
        elif content_with_prefix is not None:
            prefix_regex = (
                rf"[{''.join(comment_prefix.pattern
                if isinstance(comment_prefix,re.Pattern)
                else re.escape(comment_prefix)
                for comment_prefix in prefix)}]"
                if prefix
                else ""
            )
            comment = re.split(
                rf"(?<=^{prefix_regex})(?=.)",
                content_with_prefix,
                maxsplit=1,
            )
            if len(comment) == 2:
                self.content = comment[1].strip()
                return

        raise ExtractionError("Comment could not be extracted.")

    def to_string(self, prefix: str | None) -> str:
        """Create ini string out of the Comment.

        Args:
            prefix (str | None, optional): Prefix to use for the string. Returns to None.

        Returns:
            str: The ini string.
        """
        return f"{prefix} {self.content}" if prefix is not None else self.content


type OptionValue = Any
type OptionKey = str


class Option(SlotEntity[OptionValue]):
    """An ini option."""

    type OptionDelimiter = str | re.Pattern | tuple[str | re.Pattern, ...] | None

    def __init__(
        self,
        key: OptionKey,
        values: Any | list[Any] | None = None,
        slots: SlotAccess = None,
    ) -> None:
        """An ini option.

        Args:
            key (str | int | None, optional): The option key. Should be None if
                from_string is provided, otherwise from_string will be ignored.
                Defaults to None.
            values (Any | list[Any] | None, optional): The option value or values
                (one value per slot or one/same value for all slots). Should be None if
                from_string is provided, otherwise from_string will be ignored.
                Defaults to None.
            slots (SlotAccess, optional): Slot(s) to save value(s) in. If None, will
                create numerical slot keys starting from 0. Otherwise, number of slots
                must match number of values, unless number of values is 1 (:= same value
                for all slots). Defaults to None.
        """
        super().__init__(None)

        self.key = key

        # veryfying slots
        if slots is None:
            slots = list(range(len(values))) if isinstance(values, list) else [0]
        elif not isinstance(slots, list):
            slots = [slots]
            if isinstance(values, list):
                # in case one slot gets a list as value
                values = [values]

        if not isinstance(values, list):
            # same value for all slots
            values = [values] * len(slots)
        elif len(slots) != len(values):
            raise ValueError("Number of slots must match number of values.")

        for slot, value in zip(slots, values):
            self._slots.set_slots(
                create_missing_slots=True, new_slot_value=value, slots=slot
            )

    def to_string(self, delimiter: OptionDelimiter, *, slots: SlotAccess = None) -> str:
        """Create an ini string out of the option.

        Args:
            delimiter (OptionDelimiter): The delimiter to use for separating option key
                and value.
            slot (SlotAccess, optional): The slot to get the value from. If multiple are
                passed, will take the first that is None (or '' if all are None). If None,
                will take the first that is None of all slots. Defaults to None.

        Returns:
            str: The ini string.
        """
        slots = self._slots.slot_access(slots)
        value = next(
            (val for slot in slots if (val := self._slots[slot]) is not None), ""
        )
        return f"{self.key} {delimiter} {value}"

    @classmethod
    def from_string(
        cls, string: str, delimiter: OptionDelimiter, *, slots: SlotAccess = None
    ) -> Self:
        """Create an Option from a string.

        Args:
            string (str): The string that contains the option key and value.
            delimiter (OptionDelimiter): The delimiter that separates key and value.
            slots (SlotAccess, optional): Slot(s) to save the value in. Defaults to None.

        Returns:
            Self: A new option with the extracted key and value.
        """
        if not isinstance(delimiter, tuple):
            delimiter = (delimiter,)
        # extracting left and right side of delimiter
        lr = re.split(
            rf"[{''.join(deli.pattern
            if isinstance(deli,re.Pattern)
            else re.escape(deli)
            for deli in delimiter)}]",
            string,
            maxsplit=1,
        )

        if (
            lr
            and len(lr) == 2
            and (last_key := re.search(r"\b([\w\.\-\_]+)\b$", lr[0].strip()))
        ):
            # taking last word of left side as key
            return cls(key=last_key[0], values=lr[1].strip() or None, slots=slots)

        raise ExtractionError("Option could not be extracted.")


class CommentGroup(list[Comment]):
    """Group of comments."""

    def to_string(self, prefix: str, entity_delimiter: str) -> str:
        """Convert group of Comments to one ini string.

        Args:
            prefix (str): Prefix for the comments
            entity_delimiter (str): Entity delimiter to separate the comments.

        Returns:
            str: The Comments as one string.
        """
        return entity_delimiter.join(comment.to_string(prefix) for comment in self)


class UndefinedOption(Option):
    """Option, that is not in the provided ini schema."""

    def __init__(self, *args, **kwargs) -> None:
        # convert Option to UndefinedOption if provided
        if len(args) == 1 and not kwargs and isinstance(option := args[0], Option):
            args = ()
            kwargs = {"key": option.key, "values": list(option._slots.values())}

        super().__init__(*args, **kwargs)


class SectionName(str):

    @overload
    def __new__(cls, name: str = ..., name_with_brackets: None = ...) -> Self: ...

    @overload
    def __new__(cls, name: None = ..., name_with_brackets: str = ...) -> Self: ...

    def __new__(
        cls, name: str | None = None, name_with_brackets: str | None = None
    ) -> Self:
        """An ini section's name.

        Args:
            name (str | None, optional): Name of the section. Should be
                None if name_with_brackets is provided, otherwise name_with_brackets
                will be ignored. Defaults to None.
            name_with_brackets (str | None, optional): The name of the section within
                brackets (to extract the name from). If provided, name argument should
                be None, otherwise will be ignored. Defaults to None.
        """
        if name is not None:
            return super().__new__(cls, name)
        if name_with_brackets is not None:
            # search for opening and closing brackets at end and start of string
            if section_name := re.search(
                r"(?<=^\[).*(?=\]$)", name_with_brackets.strip()
            ):
                # remove remaining brackets from section name
                section_name = re.sub(
                    r"\]+$", "", re.sub(r"^\[+", "", section_name[0])
                ).strip()
                return super().__new__(cls, section_name)
            raise ExtractionError(
                f"Could not extract section name from {name_with_brackets}"
            )
        raise ValueError(
            "name or name_with_bracktes must be provided for"
            " initialization of a SectionName"
        )
