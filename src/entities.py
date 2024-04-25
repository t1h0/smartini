"""Ini entities are either a section name, an option or a comment."""

from typing import overload, Any, Literal, Sequence, Self
from dataclasses import dataclass
from re import split, escape, search, sub
from src.exceptions import ExtractionError
from src.args import RawRegex
from src import slots
from nomopytools.func import copy_doc


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
        prefix: ... = ...,
        content_with_prefix: str = ...,
    ) -> None: ...

    def __init__(
        self,
        content_without_prefix: str | None = None,
        prefix: str | RawRegex | tuple[str | RawRegex, ...] | None = None,
        content_with_prefix: str | None = None,
    ) -> None:
        """An ini comment.

        Args:
            content_without_prefix (str | None, optional): Content with prefix removed.
                Should be None if content_with_prefix is provided, otherwise the latter
                will be ignored. Defaults to None.
            prefix (str | tuple[str | RawRegex, ...] | None, optional): One ore more
                prefixes that denote a comment. If content_without_prefix is provieded
                and more than one prefix are given, first one will be stored.
                Defaults to None.
            content_with_prefix (str | None, optional): Content including prefix.
                Will be ignored if content_without_prefix is provided. Defaults to None.
        """
        if not isinstance(prefix, tuple):
            prefix = (prefix if prefix is not None else "",)
        assert isinstance(prefix, tuple)

        if content_without_prefix is not None:
            self.prefix = prefix[0]
            self.content = content_without_prefix
            return

        elif content_with_prefix is not None:
            prefix_regex = (
                rf"[{''.join(comment_prefix if isinstance(comment_prefix,RawRegex) else escape(comment_prefix) for comment_prefix in prefix)}]"
                if prefix
                else ""
            )
            comment = split(
                rf"(?<=^{prefix_regex})(?=.)",
                content_with_prefix,
                maxsplit=1,
            )
            if len(comment) == 2:
                self.prefix = comment[0].strip()
                self.content = comment[1].strip()
                return

        raise ExtractionError("Comment could not be extracted.")


class OptionKey(str):
    """An ini option's key."""

    pass


@dataclass(slots=True)
class OptionSlot:
    value: Any
    delimiter: str | RawRegex | None


class Option:
    """An ini option."""

    @overload
    def __init__(
        self,
        key: str = ...,
        value: ... = ...,
        delimiter: ... = ...,
        from_string: None = ...,
    ) -> None: ...
    @overload
    def __init__(
        self,
        key: None = ...,
        value: None = ...,
        delimiter: str | RawRegex | tuple[str | RawRegex, ...] = ...,
        from_string: str = ...,
    ) -> None: ...

    def __init__(
        self,
        key: str | OptionKey | None = None,
        value: str | list[str] | None = None,
        delimiter: str | RawRegex | tuple[str | RawRegex, ...] | None = None,
        from_string: str | None = None,
    ) -> None:
        """An ini option.

        Args:
            key (str | OptionKey | None, optional): The option key. Should be None if
                from_string is provided, otherwise from_string will be ignored.
                Defaults to None.
            value (str | list[str] | None, optional): The option value or values
                (one value per slot). Should be None if from_string is provided,
                otherwise from_string will be ignored. Defaults to None.
            delimiter (str | tuple[str, ...], None, optional): One or more delimiters
                that delimit key and value. Defaults to None.
            from_string (str | None, optional): A string containing key, delimiter and
                value. If provided, key or value argument must be None, otherwise will
                be ignored. Defaults to None.
        """
        self.slots: slots.Slots[OptionSlot] = []
        if key is not None:
            if not isinstance(key, str):
                raise ValueError(f"key must be string (is {type(key)})")
            self.key = OptionKey(key)
            if value is not None or delimiter is not None:
                self.slots.append(
                    OptionSlot(
                        value=value,
                        delimiter=(
                            delimiter[0] if isinstance(delimiter, tuple) else delimiter
                        ),
                    )
                )
        elif from_string is not None and delimiter is not None:
            if not isinstance(delimiter, tuple):
                delimiter = (delimiter,)
            # extracting left and right side of delimiter
            lr = split(
                rf"[{''.join(escape(deli) for deli in delimiter)}]",
                from_string,
                maxsplit=1,
            )

            if (
                lr
                and len(lr) == 2
                and (last_key := search(r"\b([\w\.\-\_]+)\b$", lr[0].strip()))
            ):
                # taking last word of left side as key
                self.key = OptionKey(last_key.group(0))
                self.slots.append(OptionSlot(lr[1].strip(), delimiter[0]))
            else:
                raise ExtractionError("Option could not be extracted.")
        else:
            raise ExtractionError("Option could not be extracted.")

    @property
    def _nslot(self) -> int:
        """Number of slots for this Option.

        Note: Private (undescore) property added for compability with interface objects
        that have _nslot properties.

        Returns:
            int: The number of slots for this Option.
        """
        return len(self.slots)

    @property
    def nslot(self) -> int:
        """Number of slots for this Option.

        Returns:
            int: The number of slots for this Option.
        """
        return self._nslot

    def set_value(
        self, value: Any, slot: slots.SlotAccess = None, add_missing_slots=True
    ) -> None:
        if isinstance(slot, int):
            if not -self.nslot <= slot < self.nslot:
                if add_missing_slots:
                    self.add_slots(slot - self.nslot + 1)
                else:
                    raise IndexError(
                        f"Slot {slot} can't be accessed because it doesn't exist."
                    )
            self[slot] = value
        elif slot is None:
            self.slots = [value] * self.nslot
        else:
            for s in slot:
                self[s] = value

    def set_values(self, values: Sequence[Any]) -> None:
        if len(values) != self.nslot:
            raise ValueError("One value per slot is required.")
        for slot, new_value in zip(self.slots, values):
            slot.value = new_value

    def add_slots(self, n=1) -> None:
        self.slots.extend(OptionSlot(None, None) for _ in range(n))

    def __getitem__(self, key: int) -> OptionSlot:
        return self.slots[key]

    def __setitem__(self, key: int, value: Any) -> None:
        if isinstance(value, OptionSlot):
            self.slots[key] = value
        else:
            self.slots[key].value = value


class UndefinedOption(Option):
    """Option, that is not in the provided ini schema."""

    def __init__(self, *args, **kwargs) -> None:
        # convert Option to UndefinedOption if provided
        if len(args) == 1 and not kwargs and isinstance(option := args[0], Option):
            args = ()
            values, delimiters = zip(
                *((slot.value, slot.delimiter) for slot in option.slots)
            )
            kwargs = {
                "key": option.key,
                "value": values,
                "delimiter": delimiters,
            }

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
            if section_name := search(r"(?<=^\[).*(?=\]$)", name_with_brackets.strip()):
                # remove remaining brackets from section name
                section_name = sub(
                    r"\]+$", "", sub(r"^\[+", "", section_name.group(0))
                ).strip()
                return super().__new__(cls, section_name)
            raise ExtractionError(
                f"Could not extract section name from {name_with_brackets}"
            )
        raise ValueError(
            "name or name_with_bracktes must be provided for"
            " initialization of a SectionName"
        )