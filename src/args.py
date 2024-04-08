from dataclasses import dataclass
from typing import Literal
from re import escape

class RawRegex(str):
    """Denotes a raw regex string. Initialize with RawRegex(r"<yourstringhere>")."""

    pass

@dataclass(slots=True)
class Parameters:
    """Ini parameters for reading and writing.
    
    Args:
        entity_delimiter (str | RawRegex, optional): Delimiter that delimits ini
            entities (section name, option, comment). Defaults to RawRegex(r"\n").
        comment_prefixes (str | RawRegex | tuple[str | RawRegex, ...], optional):
            Prefix characters that denote a comment. If multiple are given,
            the first will be taken for writing. Defaults to ";".
        option_delimiters (str | RawRegex | tuple[str | RawRegex, ...], optional):
            Delimiter characters that delimit keys from values. If multiple are
            given, the first will be taken for writing. Defaults to "=".
        continuation_allowed (bool, optional): Whether continuation of options
            (i.e. multiline options) are allowed. Defaults to True.
        continuation_prefix (str | RawRegex, optional): Prefix to denote options'
            value continuations. Defaults to RawRegex(r"\t") (TAB character).
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
    entity_delimiter: str | RawRegex = RawRegex(r"\n")
    comment_prefixes: str | RawRegex | tuple[str | RawRegex, ...] = ";"
    option_delimiters: str | RawRegex | tuple[str | RawRegex, ...] = "="
    continuation_allowed: bool = True
    continuation_prefix: str | RawRegex = RawRegex(r"\t")
    continuation_ignore: tuple[
        Literal["section", "option", "comment"],
        ...,
    ] = ()
    ignore_whitespace_lines: bool = True
    read_undefined: bool | Literal["section", "option"] = False
    
    def __post_init__(self):
        if not isinstance(self.entity_delimiter, RawRegex):
            self.entity_delimiter = RawRegex(escape(self.entity_delimiter))

        if not isinstance(self.comment_prefixes, tuple):
            self.comment_prefixes = (self.comment_prefixes,)

        if not isinstance(self.option_delimiters, tuple):
            self.option_delimiters = (self.option_delimiters,)
            
        if not isinstance(self.continuation_prefix,RawRegex):
            self.continuation_prefix = RawRegex(escape(self.continuation_prefix))