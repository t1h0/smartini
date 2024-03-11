"""Ini entities are either a section name, an option or a comment."""

from typing import overload
from typing_extensions import Self
from re import split, escape, search, sub
from src.exceptions import ExtractionError


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
        prefix: str | tuple[str, ...] | None = None,
        content_with_prefix: str | None = None,
    ) -> None:
        """An ini comment.

        Args:
            content_without_prefix (str | None, optional): Content with prefix removed.
                Should be None if content_with_prefix is provided, otherwise the latter
                will be ignored. Defaults to None.
            prefix (str | tuple[str, ...] | None, optional): Prefix that denotes the
                comment. Defaults to None.
            content_with_prefix (str | None, optional): Content including prefix.
                Will be ignored if content_without_prefix is provided. Defaults to None.
        """
        if isinstance(prefix, str):
            prefix = (prefix,)

        if content_without_prefix is not None:
            self.prefix = prefix[0] if prefix else ""
            self.content = content_without_prefix
            return

        elif content_with_prefix is not None:
            prefix_regex = (
                rf"[{''.join(escape(comment_prefix) for comment_prefix in prefix)}]"
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
        delimiter: ... = ...,
        from_string: str = ...,
    ) -> None: ...

    def __init__(
        self,
        key: str | OptionKey | None = None,
        value: str | list[str] | None = None,
        delimiter: str | tuple[str, ...] = "=",
        from_string: str | None = None,
    ) -> None:
        """An ini option.

        Args:
            key (str | OptionKey | None, optional): The option key. Should be None if
                from_string is provided, otherwise from_string will be ignored.
                Defaults to None.
            value (str | list[str] | None, optional): The option value. Should be None
                if from_string is provided, otherwise from_string will be ignored.
                Defaults to None.
            delimiter (str | tuple[str, ...], optional): The delimiter to delimit key
                and value in the ini file. Defaults to "=".
            from_string (str | None, optional): A string containing key, delimiter and
                value. If provided, key or value argument must be None, otherwise will
                be ignored. Defaults to None.
        """
        if isinstance(delimiter, str):
            delimiter = (delimiter,)

        if key is not None and value is not None:
            self.key = OptionKey(key)
            self.value = value
            self.delimiter = delimiter[0]
            return
        elif from_string is not None:
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
                self.value = lr[1].strip()
                return

        raise ExtractionError("Option could not be extracted.")


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
