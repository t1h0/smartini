"""Interface classes exist for coder interaction, to simplify the process
behind smartini."""

from pathlib import Path
from typing import Any, Type
from src.exceptions import ContinuationError, IniStructureError, ExtractionError
from src.entities import Comment, Option, SectionName, OptionKey
from src.proxies import IniProxy, SectionProxy
from re import search, escape, split, fullmatch


class RawRegex(str):
    """Denotes a raw regex string. Initialize with RawRegex(r"<yourstringhere>")."""

    pass


class _SectionMeta(type):
    """Metaclass for ini configuration file sections. Section names must be specified
    via '_name' class variable.
    """

    # name of the section. must be provided!
    _name: str

    def __new__(cls, name, bases, attrs):
        #  make sure, _name is provided
        if bases and Section in bases and "_name" not in attrs:
            raise AttributeError(
                f"Class '{name}' must define section name as '_name' class attribute."
            )
        return super().__new__(cls, name, bases, attrs)


class Section(metaclass=_SectionMeta):
    """Class for ini configuration file sections. Name of the section must be defined via
    '_name' class attribute.
    """

    # name of the section. must be provided!
    _name: str

    def __init__(self, proxy: SectionProxy) -> None:
        self._proxy = proxy

    def __getattribute__(self, __name: str) -> Any:
        proxy: SectionProxy = super().__getattribute__("_proxy")
        attribute = super().__getattribute__(__name)
        # check if attribute in proxy options, else return class attribute
        if proxy and attribute in proxy.options:
            return proxy.options[super().__getattribute__(__name)].value
        else:
            return attribute

    def __setattribute__(self, key: Any, value: Any) -> None:
        if key == "_name":
            super().__setattr__(key, value)
        elif proxy := super().__getattribute__("_proxy"):
            proxy.options[super().__getattribute__(key)].value = value


class _IniMeta(type):
    """Metaclass for Ini class. Needed for saving the non-initialized Sections to later
    initialize them.
    """

    def __new__(cls, name, bases, attrs):
        if bases and Ini in bases:
            # save sections so we can initialize them later
            attrs["_smartini_section_metas"] = tuple(
                (k, v) for k, v in attrs.items() if isinstance(v, _SectionMeta)
            )
        return super().__new__(cls, name, bases, attrs)


class Ini(metaclass=_IniMeta):

    # will be filled by metaclass
    _smartini_section_metas: tuple[tuple[str, _SectionMeta], ...]

    def __init__(
        self,
        base_path: str | Path,
        user_path: str | Path | None = None,
        entity_delimiter: str | RawRegex = RawRegex(r"\n"),
        comment_prefixes: str | RawRegex | tuple[str | RawRegex, ...] = ";",
        option_delimiters: str | RawRegex | tuple[str | RawRegex, ...] = "=",
        continuation_allowed: bool = True,
        continuation_prefix: str | RawRegex = RawRegex(r"\t"),
        continuation_ignore: (
            tuple[
                Type[SectionName] | Type[Option] | Type[Comment],
                ...,
            ]
            | None
        ) = None,
        ignore_whitespace_lines: bool = True,
    ) -> None:
        """Read a base ini and optionally update it with a user ini as long as the
        user ini's keys have valid values (invalid user keys will be ignored).

        Args:
            base_path (str | Path): Path to the base ini.
            user_path (str | Path | None, optional): Path to the user ini.
                Defaults to None.
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
            continuation_ignore (tuple[Type[SectionName] | Type[Option] | Type[Comment],
                ...] | None, optional): Entities to ignore while continuing an option's
                value. I.e. will interpret detected entities as continuation of the
                preceeding option's value if continuation rules are met (see other
                continuation arguments). Defaults to None (always interpret detected
                entities as new entities).
            ignore_whitespace_lines (bool, optional): Whether to interpret lines with
                only whitespace characters (space or tab) as empty lines.
                Defaults to True.
        """
        ### read arguments ###
        self.base_path = base_path
        self.user_path = user_path

        self.entity_delimiter = (
            entity_delimiter
            if isinstance(entity_delimiter, RawRegex)
            else escape(entity_delimiter)
        )

        self.comment_prefixes = (
            comment_prefixes
            if isinstance(comment_prefixes, tuple)
            else (comment_prefixes,)
        )
        self.option_delimiters = (
            option_delimiters
            if isinstance(option_delimiters, tuple)
            else (option_delimiters,)
        )

        self.continuation_allowed = continuation_allowed
        self.continuation_prefix = continuation_prefix
        self.continuation_ignore = continuation_ignore or ()
        # define continuation parameters
        if self.continuation_allowed:
            self.continuation_prefix_regex = (
                self.continuation_prefix
                if isinstance(self.continuation_prefix, RawRegex)
                else escape(self.continuation_prefix)
            )

        self.ignore_whitespace_lines = ignore_whitespace_lines
        # define, what defines an empty line
        self.empty_entity = r"[\s\t]*" if self.ignore_whitespace_lines else r""

        ### read inis ###
        self.cfg = self._read_ini(path=self.base_path)

        if self.user_path:
            self.user = self._read_ini(self.user_path)

            # update default ini with user ini

            for sec_name, sec in self.user.sections.items():
                for opt_key, opt in sec.options.items():
                    if (
                        sec_name in self.cfg.sections
                        and opt_key in self.cfg.sections[sec_name].options
                    ):
                        self.cfg.sections[sec_name].options[opt_key] = opt

        # initialize section metas
        for name, section in self._smartini_section_metas:
            setattr(self, name, section(self.cfg.sections[SectionName(section._name)]))

    def _read_ini(
        self,
        path: str | Path,
    ) -> IniProxy:
        """Read an ini file.

        Args:
            path (str | Path): Path to the ini file.
        """
        parsed_ini: IniProxy = IniProxy()

        with open(path, "r") as file:
            file_content = file.read()

        # split into entities
        entities = split(
            (self.entity_delimiter),
            file_content,
        )

        current_section: SectionProxy | None = None
        last_option: Option | None = None

        for entity_index, entity_content in enumerate(entities):

            # check for continuation
            possible_continuation = (
                last_option
                and self.continuation_allowed
                and (
                    continuation := search(
                        rf"(?<=^{self.continuation_prefix_regex}).*", entity_content
                    )
                )
            )

            if possible_continuation:
                # remove continuation prefix from entity content
                entity_content = continuation[0]

            if fullmatch(self.empty_entity, entity_content):
                # empty entity, skip and close off last option
                last_option = None
                continue

            # extract entity
            gates = (SectionName, Option, Comment)
            extractors = (
                lambda x: SectionName(name_with_brackets=x),
                lambda x: Option(delimiter=self.option_delimiters, from_string=x),
                lambda x: Comment(prefix=self.comment_prefixes, content_with_prefix=x),
            )

            extracted_entity = entity_content

            for gate, Extractor in zip(gates, extractors):
                # extractors are only called if set before
                if not possible_continuation or gate not in self.continuation_ignore:
                    try:
                        extracted_entity = Extractor(entity_content)
                    except ExtractionError:
                        continue
                    break

            # Handling section names

            if isinstance(extracted_entity, SectionName):
                if extracted_entity in parsed_ini.sections:
                    # section already parsed. add to it.
                    current_section = parsed_ini.sections[extracted_entity]
                else:
                    # new section
                    current_section = SectionProxy(name=extracted_entity)
                    parsed_ini.sections[extracted_entity] = current_section
                continue

            # Handling continuations

            if isinstance(extracted_entity, str):
                # processed line is just a string, therefore possible continuation
                # of latest option's value

                if not last_option:
                    # no last option (e.g. empty line after the last one)
                    raise IniStructureError(
                        f"line {entity_index} could not be assigned to a key"
                    )
                if not self.continuation_allowed:
                    raise ContinuationError(
                        f"line {entity_index} is continuation but continuation is not allowed"
                    )
                if not possible_continuation:
                    raise ContinuationError(
                        f"line {entity_index} doesn't follow continuation rules"
                    )

                # add continuation to last option
                if not isinstance(last_option.value, list):
                    last_option.value = [last_option.value]
                last_option.value.append(extracted_entity)
                continue

            # handling comments and options

            if not current_section:
                # processed line is a sectionless comment or option
                current_section = SectionProxy(name=None)
                parsed_ini.sections[None] = current_section

            # add comment or option to current section's structure
            current_section.structure.append(extracted_entity)

            if isinstance(extracted_entity, Option):
                # add option to current section's options
                last_option = extracted_entity
                current_section.options[extracted_entity.key] = extracted_entity

        return parsed_ini
