from typing import Literal, Any
import re
from .entities import Option, Comment
from .type_converters.converters import TypeConverter, DEFAULT_GUESS_CONVERTER, ConvertibleTypes


class Parameters:
    """Parameters for reading and writing."""

    def __init__(
        self,
        entity_delimiter: str | re.Pattern = re.compile("\n"),
        comment_prefixes: Comment.Prefix | tuple[Comment.Prefix, ...] = ";",
        option_delimiters: Option.Delimiter | tuple[Option.Delimiter, ...] = "=",
        multiline_allowed: bool = True,
        multiline_prefix: str | re.Pattern | None = None,
        multiline_ignore: (
            tuple[
                Literal["section_name", "option_delimiter", "comment_prefix"],
                ...,
            ]
            | None
        ) = (),
        ignore_whitespace_lines: bool = True,
        read_undefined: bool | Literal["section", "option"] = False,
        type_converter: type[TypeConverter | ConvertibleTypes] | None = DEFAULT_GUESS_CONVERTER,
    ) -> None:
        """
        Args:
            entity_delimiter (str | re.Pattern, optional): Delimiter that delimits
                entities (section name, option, comment). Defaults to re.Pattern("\n").
            comment_prefixes (Comment.Prefix | tuple[Comment.Prefix,...], optional):
                Prefix character(s) that denote a comment. If multiple are given,
                the first will be taken for writing. "[" is not allowed. Defaults to ";".
            option_delimiters (Option.Delimiter | tuple[Option.Delimiter,...], optional):
                Delimiter character(s) that delimit option keys from values. If multiple
                are given, the first will be taken for writing. "[" is not allowed.
                Defaults to "=".
            multiline_allowed (bool, optional): Whether continuations of options
                (i.e. multiline options) are allowed. If False, will throw a
                ContinuationError for any continuation. Defaults to True.
            multiline_prefix (str | re.Pattern | None, optional): Prefix to denote
                continuations of multiline options. If set, will only accept
                continuations with that prefix (will throw a ContinuationError if that
                prefix is missing). Defaults to None (possible continuation after one
                entity delimiter).
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
            type_converter (type[TypeConverter | ConvertibleTypes] | None, optional):
                TypeConverter to apply to every option value (and continuation) that is
                not explicitly annotated. Alternatively one of the ConvertibleTypes that
                the respective option values should be interpreted as (will be matched
                to a TypeConverter). If None, will save all values (and continuations)
                as strings. Defaults to smartini.type_converters.DEFAULT_GUESS_CONVERTER.
        """
        # because comment_prefixes and option_delimiters check each other on setting
        self._comment_prefixes = ()
        self._option_delimiters = ()

        self.entity_delimiter = entity_delimiter
        self.comment_prefixes = comment_prefixes
        self.option_delimiters = option_delimiters
        self.multiline_allowed = multiline_allowed
        self.multiline_prefix = multiline_prefix
        self.multiline_ignore = multiline_ignore
        self.ignore_whitespace_lines = ignore_whitespace_lines
        self.read_undefined = read_undefined
        self.type_converter = type_converter

    @property
    def entity_delimiter(self) -> str:
        return self._entity_delimiter

    @entity_delimiter.setter
    def entity_delimiter(self, value: str | re.Pattern) -> None:
        self._entity_delimiter = (
            value.pattern if isinstance(value, re.Pattern) else re.escape(value)
        )

    @property
    def comment_prefixes(self) -> tuple[str, ...]:
        return self._comment_prefixes

    @comment_prefixes.setter
    def comment_prefixes(
        self, value: Comment.Prefix | tuple[Comment.Prefix, ...]
    ) -> None:
        if not isinstance(value, tuple):
            value = (value,)
        value = tuple(
            val.pattern if isinstance(val, re.Pattern) else re.escape(val)
            for val in value
        )
        if any(val.startswith(re.escape("[")) for val in value):
            raise ValueError(
                "'[' (section name identifier) is not allowed as a comment prefix."
            )
        if set(value).intersection(self.option_delimiters):
            raise ValueError(
                "Option delimiters and comment prefixes have to be distinct from another."
            )
        self._comment_prefixes = value

    @property
    def option_delimiters(self) -> tuple[str, ...]:
        return self._option_delimiters

    @option_delimiters.setter
    def option_delimiters(
        self, value: Option.Delimiter | tuple[Option.Delimiter, ...]
    ) -> None:
        if not isinstance(value, tuple):
            value = (value,)
        value = tuple(
            val.pattern if isinstance(val, re.Pattern) else re.escape(val)
            for val in value
        )
        if any(val.startswith(re.escape("[")) for val in value):
            raise ValueError(
                "'[' (section name identifier) is not allowed as an option delimiter."
            )
        if set(value).intersection(self.comment_prefixes):
            raise ValueError(
                "Option delimiters and comment prefixes have to be distinct from another."
            )
        self._option_delimiters = value

    @property
    def multiline_prefix(self) -> str:
        return self._multiline_prefix

    @multiline_prefix.setter
    def multiline_prefix(self, value: str | re.Pattern | None) -> None:
        if value is None:
            self._multiline_prefix = ""
        elif isinstance(value, re.Pattern):
            self._multiline_prefix = value.pattern
        else:
            self._multiline_prefix = re.escape(value)

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

    def update(self, **kwargs) -> None:
        """Update parameters with kwargs

        Args:
            **kwargs: Keyword-arguments to update the parameters with.
        """
        for k, v in kwargs.items():
            setattr(self, k, v)
