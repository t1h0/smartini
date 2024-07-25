from typing import Literal, Any
import re
from .entities import Option, Comment
from .type_converters.converters import (
    TypeConverter,
    DEFAULT_GUESS_CONVERTER,
    DEFAULT_STRING_CONVERTER,
    ConvertibleTypes,
    _type_hint_to_converter,
)
from .globals import VALID_MARKERS


class Parameters:
    """Parameters for reading and writing."""

    def __init__(
        self,
        comment_prefixes: VALID_MARKERS | tuple[VALID_MARKERS, ...] | None = ";",
        option_delimiters: VALID_MARKERS | tuple[VALID_MARKERS, ...] = "=",
        multiline_allowed: bool = True,
        multiline_prefix: VALID_MARKERS | Literal["\t"] | None = None,
        multiline_ignore: (
            tuple[
                Literal["section_name", "option_delimiter", "comment_prefix"],
                ...,
            ]
            | None
        ) = (),
        ignore_whitespace_lines: bool = True,
        read_undefined: bool | Literal["section", "option"] = False,
        default_type_converter: (
            type[TypeConverter | ConvertibleTypes] | None
        ) = DEFAULT_GUESS_CONVERTER,
    ) -> None:
        """
        Args:
            comment_prefixes (VALID_MARKERS | tuple[VALID_MARKERS,...] | None,
                optional): Prefix character(s) that denote a comment. If multiple are given,
                the first will be taken for writing. If None, will treat every line as
                comment that is not an option or section name. Defaults to ";".
            option_delimiters (VALID_MARKERS | tuple[VALID_MARKERS,...], optional):
                Delimiter character(s) that delimit option keys from values. If multiple
                are given, the first will be taken for writing. Defaults to "=".
            multiline_allowed (bool, optional): Whether continuations of options
                (i.e. multiline options) are allowed. If False, will throw a
                ContinuationError for any continuation. Defaults to True.
            multiline_prefix (VALID_MARKERS | Literal["\t"] | None, optional): Prefix to
                denote continuations of multiline options. If set, will only accept
                continuations with that prefix (will throw a ContinuationError if that
                prefix is missing). Defaults to None (possible continuation without
                prefix).
            multiline_ignore (tuple["section_name" | "option_delimiter" |
                "comment_prefix", ...] | None, optional): Entity identifier(s) to ignore
                while continuing an option's value. Otherwise lines with those identifiers
                will be interpreted as a new entity instead of a continuation (despite
                possibly satisfying multiline rules). Useful if a continuation is
                possibly in brackets (otherwise interpreted as a section name), contains
                the option delimiter (e.g. URLs often include a "=") or starts with a
                comment prefix. Defaults to None.
            ignore_whitespace_lines (bool, optional): Whether to interpret lines with
                only whitespace characters (space or tab) as empty lines.
                Defaults to True.
            read_undefined (bool | "section" | "option", optional):
                Whether undefined content should be read and stored. If True, will read
                every undefined content. If "section", will read undefined sections
                and their content but not undefined options within defined sections.
                "option" will read undefined options within defined sections but
                not undefined sections and their content. If False, will ignore
                undefined content. Defaults to False.
            default_type_converter (type[TypeConverter | ConvertibleTypes] | None, optional):
                TypeConverter to apply to every option value (and continuation) that is
                not explicitly annotated. Alternatively one of the ConvertibleTypes that
                the respective option values should be interpreted as (will be matched
                to a TypeConverter). If None, will save all values (and continuations)
                as strings. Defaults to smartini.type_converters.DEFAULT_GUESS_CONVERTER.
        """
        # because comment_prefixes and option_delimiters check each other on setting
        self._comment_prefixes = ()
        self._option_delimiters = ()

        self.comment_prefixes = comment_prefixes
        self.option_delimiters = option_delimiters
        self.multiline_allowed = multiline_allowed
        self.multiline_prefix = multiline_prefix
        self.multiline_ignore = multiline_ignore
        self.ignore_whitespace_lines = ignore_whitespace_lines
        self.read_undefined = read_undefined
        self.default_type_converter = default_type_converter

    @property
    def comment_prefixes(self) -> tuple[VALID_MARKERS, ...] | None:
        return self._comment_prefixes

    @comment_prefixes.setter
    def comment_prefixes(
        self, value: VALID_MARKERS | tuple[VALID_MARKERS, ...] | None
    ) -> None:
        if value is not None:
            if not isinstance(value, tuple):
                value = (value,)
            self.verify_marker(value, "comment prefix")
        self._comment_prefixes = value
        self.verify_between_markers()

    @property
    def option_delimiters(self) -> tuple[VALID_MARKERS, ...]:
        return self._option_delimiters

    @option_delimiters.setter
    def option_delimiters(
        self, value: VALID_MARKERS | tuple[VALID_MARKERS, ...]
    ) -> None:
        if not isinstance(value, tuple):
            value = (value,)
        self.verify_marker(value, "option delimiter")
        self._option_delimiters = value
        self.verify_between_markers()

    @property
    def multiline_prefix(self) -> str:
        return self._multiline_prefix

    @multiline_prefix.setter
    def multiline_prefix(self, value: VALID_MARKERS | Literal["\t"] | None) -> None:
        if value is None:
            self._multiline_prefix = ""
        else:
            self._multiline_prefix = re.escape(value)
        self.verify_between_markers()

    @property
    def multiline_ignore(self) -> tuple[
        Literal["section_name", "option_delimiter", "comment_prefix"],
        ...,
    ]:
        return self._multiline_ignore

    @multiline_ignore.setter
    def multiline_ignore(
        self,
        value: (
            tuple[
                Literal["section_name", "option_delimiter", "comment_prefix"],
                ...,
            ]
            | None
        ),
    ) -> None:
        self._multiline_ignore = () if value is None else value

    @property
    def default_type_converter(self) -> type[TypeConverter] | None:
        return self._default_type_converter

    @default_type_converter.setter
    def default_type_converter(
        self, value: type[TypeConverter | ConvertibleTypes] | None
    ) -> None:
        self._default_type_converter = (
            DEFAULT_STRING_CONVERTER
            if value is None
            else _type_hint_to_converter(value)
        )

    def verify_marker(self, marker: tuple[str, ...], name: str) -> None:
        for val in marker:
            if val.startswith(re.escape("[")):
                raise ValueError(
                    f"'[' (section name identifier) is not allowed as a {name}."
                )
            if re.escape(",") in val:
                raise ValueError(f"Comma is not allowed inside of a {name}.")

    def verify_between_markers(self) -> None:
        if hasattr(self, "comment_prefixes") and self.comment_prefixes:
            cps = set(self.comment_prefixes)
            if hasattr(self, "option_delimiters") and cps.intersection(
                self.option_delimiters
            ):
                raise ValueError(
                    "Comment prefixes and option delimiters have to be distinct from each other."
                )
            if hasattr(self, "multiline_prefix") and cps.intersection(
                set(self.multiline_prefix)
            ):
                raise ValueError(
                    "Comment prefixes and multiline prefix have to be distinct from each other."
                )
        if hasattr(self, "multiline_prefix") and set(
            self.multiline_prefix
        ).intersection(self.option_delimiters):
            raise ValueError(
                "Multiline prefix and option delimiters have to be distinct from each other."
            )

    def update(self, **kwargs) -> None:
        """Update parameters with kwargs

        Args:
            **kwargs: Keyword-arguments to update the parameters with.
        """
        for k, v in kwargs.items():
            setattr(self, k, v)
