from typing import Literal
import re


class Parameters:

    def __init__(
        self,
        entity_delimiter: str | re.Pattern = re.compile("\n"),
        comment_prefixes: str | re.Pattern | tuple[str | re.Pattern, ...] = ";",
        option_delimiters: str | re.Pattern | tuple[str | re.Pattern, ...] = "=",
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
    ) -> None:
        """Parameters for reading and writing.

        Args:
            entity_delimiter (str | re.Pattern, optional): Delimiter that delimits
                entities (section name, option, comment). Defaults to re.Pattern("\n").
            comment_prefixes (str | re.Pattern | tuple[str | re.Pattern, ...], optional):
                Prefix characters that denote a comment. If multiple are given,
                the first will be taken for writing. "[" is not allowed. Defaults to ";".
            option_delimiters (str | re.Pattern | tuple[str | re.Pattern, ...], optional):
                Delimiter characters that delimit option keys from values. If multiple
                are given, the first will be taken for writing. Defaults to "=".
            multiline_allowed (bool, optional): Whether continuations of options
                (i.e. multiline options) are allowed. If False, will throw a
                ContinuationError for any continuation. Defaults to True.
            multiline_prefix (str | re.Pattern | None, optional): Prefix to denote
                continuations of multiline options. If set, will only accept
                continuations with that prefix (will throw a ContinuationError if that
                prefix is missing). Defaults to None (possible continuation after one
                entity delimiter).
            multiline_ignore (tuple["section_name" | "option_delimiter" |
                "comment_prefix", ...] | None, optional): Entitity identifier(s) to ignore
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
                "option" will read undefinied options within defined sections but
                not undefined sections and their content. If False, will ignore
                undefined content. Defaults to False.
        """

        self.entity_delimiter = entity_delimiter
        self.comment_prefixes = comment_prefixes
        self.option_delimiters = option_delimiters
        self.multiline_allowed = multiline_allowed
        self.multiline_prefix = multiline_prefix
        self.multiline_ignore = multiline_ignore
        self.ignore_whitespace_lines = ignore_whitespace_lines
        self.read_undefined = read_undefined

        self.validate_parameters()

    def update(self, **kwargs) -> None:
        """Update parameters with kwargs

        Args:
            **kwargs: Keyword-arguments to update the parameters with.
        """

        for k, v in kwargs.items():
            setattr(self, k, v)
        self.validate_parameters(*kwargs.keys())

    def validate_parameters(self, *params) -> None:
        """Validate parameters for correct functionality."""

        if not params or "entity_delimiter" in params:
            self.entity_delimiter = (
                self.entity_delimiter.pattern
                if isinstance(self.entity_delimiter, re.Pattern)
                else re.escape(self.entity_delimiter)
            )

        if not params or "comment_prefixes" in params:
            if not isinstance(self.comment_prefixes, tuple):
                self.comment_prefixes = (self.comment_prefixes,)
            if "[" in self.comment_prefixes:
                raise ValueError(
                    "'[' (section name identifier) is not allowed as a comment prefix."
                )

        if (not params or "option_delimiters" in params) and not isinstance(
            self.option_delimiters, tuple
        ):
            self.option_delimiters = (self.option_delimiters,)

        if not params or "continuation_prefix" in params:
            self.multiline_prefix = (
                ""
                if self.multiline_prefix is None
                else (
                    self.multiline_prefix.pattern
                    if isinstance(self.multiline_prefix, re.Pattern)
                    else re.escape(self.multiline_prefix)
                )
            )

        if (
            not params or "continuation_ignore" in params
        ) and self.multiline_ignore is None:
            self.multiline_ignore = ()
