"""Ini entities are either a section name, an option or a comment."""

from typing import overload, Any, Self, cast
from dataclasses import dataclass
import re
from .exceptions_warnings import ExtractionError
from .slots import SlotAccess, _SlotEntity
from .type_converters.converters import (
    TypeConverter,
    ConvertibleTypes,
    _type_to_converter,
)
from .globals import VALID_MARKERS, VALID_MULTILINE_PREFIX


class Comment:
    """Comment object holding a comment's content."""

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
        prefix: VALID_MARKERS | tuple[VALID_MARKERS, ...] | None = ...,
        content_with_prefix: str = ...,
    ) -> None: ...

    def __init__(
        self,
        content_without_prefix: str | None = None,
        prefix: VALID_MARKERS | tuple[VALID_MARKERS, ...] | None = None,
        content_with_prefix: str | None = None,
    ) -> None:
        """
        Args:
            content_without_prefix (str | None, optional): Content with prefix removed.
                Should be None if content_with_prefix is provided, otherwise the latter
                will be ignored. Defaults to None.
            prefix (VALID_MARKERS | tuple[VALID_MARKERS, ...] | None, optional):
                One or more prefixes that can denote the comment (used for
                content_with_prefix). Defaults to None.
            content_with_prefix (str | None, optional): Content including prefix.
                Will be ignored if content_without_prefix is provided. Defaults to None.
        """
        if not isinstance(prefix, tuple) and prefix is not None:
            prefix = (prefix,)
        assert isinstance(prefix, tuple)

        if content_without_prefix is not None:
            self.content = content_without_prefix
            return
        elif content_with_prefix is not None:
            prefix_regex = (
                rf"[{''.join(re.escape(comment_prefix)
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

    def to_string(self, prefix: str | None = None) -> str:
        """Convert the Comment into an ini string.

        Args:
            prefix (str | None, optional): Prefix to use for the string.
                Defaults to None.

        Returns:
            str: The ini string.
        """
        return f"{prefix} {self.content}" if prefix is not None else self.content

    def __str__(self) -> str:
        return self.to_string()


type OptionValue = Any
"""An option's value."""
type OptionKey = str
"""An option's key."""


class OptionValueMultiline(list[Any]):
    """A multiline option value."""

    def to_string(self, multiline_prefix: VALID_MULTILINE_PREFIX = None):
        """Convert the multiline option value to a string.

        Args:
            multiline_prefix (VALID_MULTILINE_PREFIX, optional): Prefix to add to each line.
                If None, won't add a prefix. Defaults to None.

        Returns:
            str: The multiline option value as a string.
        """
        str_items = (str(i) for i in self)
        if multiline_prefix is None:
            return "\n".join(str_items)
        else:
            return f"\n{multiline_prefix}".join(str_items)


@dataclass(slots=True)
class OptionSlotValue:
    """Value of one Option slot.

    Args:
        input (OptionValue): The original input value.
        converted (OptionValue): The converted input if TypeConverter was set, otherwise
            the input again.
    """

    input: OptionValue | None = None
    converted: OptionValue | None = None

    def to_string(self, multiline_prefix: VALID_MULTILINE_PREFIX = None) -> str:
        """Convert the OptionSlotValue to a string.

        Args:
            multiline_prefix (VALID_MULTILINE_PREFIX, optional): Prefix to add to each line.
                If None, won't add a prefix. Defaults to None.

        Returns:
            str: The converted string.
        """
        if isinstance(self.input, OptionValueMultiline):
            return self.input.to_string(multiline_prefix)
        if self.input is None:
            return ""
        return str(self.input)


class Option(_SlotEntity[OptionSlotValue]):
    """Option object holding an option's value (per slot) and key."""

    def __new__[T](
        cls,
        key: OptionKey = "",
        typ: type[T] = type[ConvertibleTypes],
        type_converter: TypeConverter | None = None,
        values: Any | list[Any] | None = None,
        slots: SlotAccess = None,
    ) -> T:
        return cast(typ, super().__new__(cls))

    def __init__(
        self,
        key: OptionKey,
        typ: type | None = None,
        type_converter: TypeConverter | None = None,
        values: Any | list[Any] | None = None,
        slots: SlotAccess = None,
    ) -> None:
        """
        Args:
            key (str | int | None, optional): The option key. Should be None if
                from_string is provided, otherwise from_string will be ignored.
                Defaults to None.
            typ (type | None, optional): The type the option value should be converted
                to. Will also be used for type guessing if type_converter is None.
                Defaults to None.
            type_converter (TypeConverter | None, optional): The TypeConverter to apply
                whenever a new value is set. Overrides type guessing by typ.
                If None will not apply. Defaults to None.
            values (Any | list[Any] | None, optional): The option value or values
                (one value per slot or one/same value for all slots). Should be None if
                from_string is provided, otherwise from_string will be ignored.
                Defaults to None.
            slots (SlotAccess, optional): Slot(s) to save value(s) in. If None, will
                create numerical slot keys starting from 0. Otherwise, number of slots
                must match number of values, unless number of values is 1 (:= same value
                for all slots). Defaults to None.
        """
        super().__init__(OptionSlotValue)

        self.key = key
        self._type_converter = type_converter or _type_to_converter(typ)

        # verifying slots
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
            self._set_slots(create_missing_slots=True, value=value, slots=slot)

    def _set_slots(
        self,
        value: OptionValue | OptionSlotValue,
        create_missing_slots=False,
        *,
        slots: SlotAccess = None,
    ) -> None:
        """Set the content of specified slots.

        Args:
            value (OptionValue | OptionSlotValue): New value for the slots.
            create_missing_slots (bool, optional): Whether to create slots that are
                specified but don't exist in the entity. Defaults to False.
            slots (SlotAccess, optional): Slots to set. Defaults to None.
        """
        input_value = value.input if isinstance(value, OptionSlotValue) else value
        converted_value = (
            value.converted if isinstance(value, OptionSlotValue) else value
        )

        def slot_value():
            return OptionSlotValue(
                input=input_value,
                converted=(
                    self._type_converter(input_value)
                    if self._type_converter and input_value is not None
                    else converted_value
                ),
            )

        return super()._set_slots(
            value=slot_value,
            create_missing_slots=create_missing_slots,
            slots=slots,
        )

    def to_string(
        self,
        delimiter: VALID_MARKERS,
        multiline_prefix: VALID_MULTILINE_PREFIX = None,
        *,
        slots: SlotAccess = None,
    ) -> str:
        """Convert the Option into an ini string.

        Args:
            delimiter (VALID_MARKERS): The delimiter to use for separating option key
                and value.
            multiline_prefix (VALID_MULTILINE_PREFIX, optional): Prefix to add to each
                line for multiline values. If None, won't add a prefix. Defaults to None.
            slot (SlotAccess, optional): The slot to get the value from. If multiple are
                passed, will take the first that is not None (or return an empty string
                if all are None). If None, will take the first that is not None
                of all slots. Defaults to None.

        Returns:
            str: The ini string.
        """
        slots = self._slots.slot_access(slots)
        value = next(
            (
                val.to_string(multiline_prefix)
                for slot in slots
                if (val := self._slots[slot]) != ""
            ),
            "",
        )
        return f"{self.key} {delimiter} {value}"

    def __str__(self) -> str:
        return self.to_string("=")

    @classmethod
    def from_string(
        cls,
        string: str,
        delimiter: VALID_MARKERS | tuple[VALID_MARKERS, ...],
        type_converter: TypeConverter | None = None,
        *,
        slots: SlotAccess = None,
    ) -> Self:
        """Create an Option from a string.

        Args:
            string (str): The string that contains the option key and value.
            delimiter (VALID_MARKERS | tuple[VALID_MARKERS, ...]): One or more
                delimiters that can separates option key and value. Defaults to None.
            type_converter (TypeConverter | None, optional): A TypeConverter
                to apply. If None will not convert. Defaults to None.
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
            return cls(
                key=last_key[0],
                values=lr[1].strip() or None,
                type_converter=type_converter,
                slots=slots,
            )

        raise ExtractionError("Option could not be extracted.")

    def add_continuation(
        self,
        continuation: str,
        type_converter: TypeConverter | None = None,
        *,
        slots: SlotAccess,
    ) -> None:
        """Adds a continuation to the selected slots.

        Args:
            continuation (str): The continuation to add to the slot values.
            type_converter (type[TypeConverter] | None, optional): The type converter
                to use if self.type_converter is None. If None, will save as string in
                the latter case. Defaults to None.
            slots (SlotAccess): The slots to access.
        """
        slots = self._slots.slot_access(slots)
        for slot in slots:
            _input = self._slots[slot].input
            if not isinstance(_input, OptionValueMultiline):
                _input = OptionValueMultiline((_input,))
            _input.append(continuation)
            converted = OptionValueMultiline(
                (
                    self._type_converter(i)
                    if self._type_converter
                    else type_converter(i) if type_converter else i
                )
                for i in _input
            )
            self._slots[slot].converted = converted
            self._slots[slot].input = _input


class CommentGroup(list[Comment]):
    """Group of Comments."""

    def to_string(self, prefix: str | None = None) -> str:
        """Convert group of Comments to one ini string.

        Args:
            prefix (str | None, optional): Prefix for the comments. If None, won't add
                a prefix. Defaults to None.

        Returns:
            str: The Comments as one string.
        """
        return "\n".join(comment.to_string(prefix) for comment in self)

    def __str__(self) -> str:
        return self.to_string()


class UndefinedOption(Option):
    """Option, that is not hard coded in the provided schema."""

    def __new__(cls, *args, **kwargs):
        return super().__new__(*args, **kwargs)

    def __init__(self, *args, **kwargs) -> None:
        """Takes args and kwargs identical to Option. Can also take an Option to copy its
        attributes.
        """
        # convert Option to UndefinedOption if provided
        if len(args) == 1 and not kwargs and isinstance(option := args[0], Option):
            args = ()
            kwargs = {
                "key": option.key,
                "values": list(option._slots.values()),
                "type_converter": option._type_converter,
            }

        super().__init__(*args, **kwargs)


class SectionName(str):
    """A configuration section's name."""

    @overload
    def __new__(cls, name: str = ..., name_with_brackets: None = ...) -> Self: ...

    @overload
    def __new__(cls, name: None = ..., name_with_brackets: str = ...) -> Self: ...

    def __new__(
        cls, name: str | None = None, name_with_brackets: str | None = None
    ) -> Self:
        """
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
            "name or name_with_brackets must be provided for"
            " initialization of a SectionName"
        )
