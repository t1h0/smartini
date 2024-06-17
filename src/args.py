from typing import Literal
import re


class Parameters:
    """Ini parameters for reading and writing.

    Args:
        entity_delimiter (str | re.Pattern, optional): Delimiter that delimits ini
            entities (section name, option, comment). Defaults to re.Pattern("\n").
        comment_prefixes (str | re.Pattern | tuple[str | re.Pattern, ...], optional):
            Prefix characters that denote a comment. If multiple are given,
            the first will be taken for writing. Defaults to ";".
        option_delimiters (str | re.Pattern | tuple[str | re.Pattern, ...], optional):
            Delimiter characters that delimit keys from values. If multiple are
            given, the first will be taken for writing. Defaults to "=".
        continuation_allowed (bool, optional): Whether continuation of options
            (i.e. multiline options) are allowed. Defaults to True.
        continuation_prefix (str | re.Pattern, optional): Prefix to denote options'
            value continuations. Defaults to re.Pattern("\t") (TAB character).
        continuation_ignore (tuple["section" | "option" | "comment", ...], optional):
            Entities to ignore while continuing an option's value.
            I.e. will interpret detected entities as continuation of the
            preceeding option's value if continuation rules are met (see other
            continuation arguments). Defaults to empty tuple (:= interpret all
            detected entities as new entities).
        ignore_whitespace_lines (bool, optional): Whether to interpret lines with
            only whitespace characters (space or tab) as empty lines.
            Defaults to True.
        read_undefined (bool | "section" | "option", optional):
            Whether undefined content should be read and stored. If true, will read
            every undefined content. If type[Section], will read undefined sections
            and their content but not undefined options within defined sections.
            type[Option] will read undefinied options within defined sections but
            not undefined sections and their content. If False, will ignore
            undefined content. Defaults to False.
    """

    def __init__(
        self,
        entity_delimiter: str | re.Pattern = re.compile("\n"),
        comment_prefixes: str | re.Pattern | tuple[str | re.Pattern, ...] = ";",
        option_delimiters: str | re.Pattern | tuple[str | re.Pattern, ...] = "=",
        continuation_allowed: bool = True,
        continuation_prefix: str | re.Pattern = re.compile("\t"),
        continuation_ignore: tuple[
            Literal["section", "option", "comment"],
            ...,
        ] = (),
        ignore_whitespace_lines: bool = True,
        read_undefined: bool | Literal["section", "option"] = False,
    ) -> None:

        self.entity_delimiter = entity_delimiter
        self.comment_prefixes = comment_prefixes
        self.option_delimiters = option_delimiters
        self.continuation_allowed = continuation_allowed
        self.continuation_prefix = continuation_prefix
        self.continuation_ignore = continuation_ignore
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
        if not params or "entity_delimiter" in params:
            self.entity_delimiter = (
                self.entity_delimiter.pattern
                if isinstance(self.entity_delimiter, re.Pattern)
                else re.escape(self.entity_delimiter)
            )
        if not params or "comment_prefixes" in params:
            self.comment_prefixes = (
                self.comment_prefixes
                if isinstance(self.comment_prefixes, tuple)
                else (self.comment_prefixes,)
            )
        if not params or "option_delimiters" in params:
            self.option_delimiters = (
                self.option_delimiters
                if isinstance(self.option_delimiters, tuple)
                else (self.option_delimiters,)
            )
        if not params or "continuation_prefix" in params:
            self.continuation_prefix = (
                self.continuation_prefix.pattern
                if isinstance(self.continuation_prefix, re.Pattern)
                else re.escape(self.continuation_prefix)
            )
