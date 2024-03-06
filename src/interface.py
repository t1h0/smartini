from pathlib import Path
from typing import Any, Literal
from src.nomotools.collections import OrderedDict
from src.exceptions import *
from re import search, escape, split, fullmatch
from dataclasses import dataclass, field


@dataclass
class _Comment:
    content: str
    delimiter: str


class _OptionKey(str):
    pass


@dataclass
class _Option:
    key: _OptionKey
    value: str | list[str] | None


class _SectionName(str):
    pass


class RawRegex(str):
    pass


@dataclass
class SectionProxy:
    name: _SectionName | None
    structure: list[_Comment | _Option] = field(default_factory=list)
    options: OrderedDict[_OptionKey, _Option] = field(default_factory=OrderedDict)


@dataclass
class ParsedIni:
    sections: OrderedDict[_SectionName, SectionProxy] = field(
        default_factory=OrderedDict
    )


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
        if proxy and attribute in proxy.options:
            return proxy.options[super().__getattribute__(__name)].value
        else:
            return attribute

    def __setattribute__(self, key: Any, value: Any) -> None:
        proxy: SectionProxy = super().__getattribute__("_proxy")
        if proxy:
            proxy.options[super().__getattribute__(key)].value = value


class _IniMeta(type):

    def __new__(cls, name, bases, attrs):
        if bases and Ini in bases:
            # save sections so we can initialize them later
            attrs["_smartini_section_metas"] = tuple(
                (k, v) for k, v in attrs.items() if isinstance(v, _SectionMeta)
            )
        return super().__new__(cls, name, bases, attrs)


class Ini(metaclass=_IniMeta):

    _smartini_section_metas: tuple[tuple[str, _SectionMeta], ...]

    def __init__(
        self,
        default: str | Path,
        user: str | Path | None = None,
        entity_delimiter: str | RawRegex = RawRegex(r"\n"),
        comment_prefixes: str | RawRegex | tuple[str | RawRegex, ...] = ";",
        option_delimiters: str | RawRegex | tuple[str | RawRegex, ...] = "=",
        continuation_allowed: (
            tuple[
                Literal["section_start"]
                | Literal["comment_prefix"]
                | Literal["option_delimiter"],
                ...,
            ]
            | bool
        ) = True,
        continuation_prefix: str | RawRegex = RawRegex(r"\t"),
        ignore_whitespace_lines: bool = True,
    ) -> None:
        """Read a default ini and optionally update it with a user ini as long as the
        user ini's keys have valid values (invalid user keys will be ignored).

        Args:
            default (str | Path): Path to the default ini.
            user (str | Path | None, optional): Path to the user ini. Defaults to None.
            comment_prefixes (str | tuple[str,...], optional): Prefix characters to
                denote a comment. If multiple are given, the first will be taken
                for writing. Defaults to ";".
            option_delimiters (str | tuple[str,...], optional): Delimiter characters to
                delimit keys from values. If multiple are given, the first will be taken
                for writing. Defaults to "=".
        """
        if not isinstance(comment_prefixes, tuple):
            comment_prefixes = (comment_prefixes,)
        if not isinstance(option_delimiters, tuple):
            option_delimiters = (option_delimiters,)
        cfg = self._read_ini(
            path=default,
            entity_delimiter=entity_delimiter,
            comment_prefixes=comment_prefixes,
            option_delimiters=option_delimiters,
            continuation_allowed=continuation_allowed,
            continuation_prefix=continuation_prefix,
            ignore_whitespace_lines=ignore_whitespace_lines,
        )

        if user:
            user_cfg = self._read_ini(
                path=user,
                entity_delimiter=entity_delimiter,
                comment_prefixes=comment_prefixes,
                option_delimiters=option_delimiters,
                continuation_allowed=continuation_allowed,
                continuation_prefix=continuation_prefix,
                ignore_whitespace_lines=ignore_whitespace_lines,
            )

            # update default ini with user ini

            for sec_name, sec in user_cfg.sections.items():
                for opt_key, opt in sec.options.items():
                    if (
                        sec_name in cfg.sections
                        and opt_key in cfg.sections[sec_name].options
                    ):
                        cfg.sections[sec_name].options[opt_key] = opt

        self._init_section_metas(cfg)

        self.CONFIG = cfg

    def _read_ini(
        self,
        path: str | Path,
        entity_delimiter: str | RawRegex,
        comment_prefixes: tuple[str | RawRegex, ...],
        option_delimiters: tuple[str | RawRegex, ...],
        continuation_allowed: (
            tuple[
                Literal["section_start"]
                | Literal["comment_prefix"]
                | Literal["option_delimiter"],
                ...,
            ]
            | bool
        ),
        continuation_prefix: str | RawRegex,
        ignore_whitespace_lines: bool,
    ) -> ParsedIni:

        parsed_ini: ParsedIni = ParsedIni()

        with open(path, "r") as file:
            file_content = file.read()

        # define, what defines an empty line
        empty_entity = r"[\s\t]*" if ignore_whitespace_lines else r""

        # define continuation parameters
        if continuation_allowed:
            continuation_prefix_regex = (
                continuation_prefix
                if isinstance(continuation_prefix, RawRegex)
                else escape(continuation_prefix)
            )
            if isinstance(continuation_allowed, bool):
                continuation_allowed = (True,)
        else:
            continuation_allowed = tuple()
        assert isinstance(continuation_allowed, tuple)

        # split into entities
        entities = split(
            (
                entity_delimiter
                if isinstance(entity_delimiter, RawRegex)
                else escape(entity_delimiter)
            ),
            file_content,
        )

        current_section: SectionProxy | None = None
        last_option: _Option | None = None

        for entity_index, entity_content in enumerate(entities):

            possible_continuation = (
                last_option
                and continuation_allowed
                and (
                    continuation := search(
                        rf"(?<=^{continuation_prefix_regex}).*", entity_content
                    )
                )
            )

            if possible_continuation:
                # remove continuation prefix from entity content
                entity_content = continuation.group(0)

            if fullmatch(empty_entity, entity_content):
                # empty entity, skip and close off last option
                last_option = None
                continue

            extract_option = (
                not possible_continuation
                or "option_delimiter" not in continuation_allowed
            )
            extract_comment = (
                not possible_continuation
                or "comment_prefix" not in continuation_allowed
            )
            extract_section = (
                not possible_continuation or "section_start" not in continuation_allowed
            )

            # extract entity
            extracted_entity = entity_content
            # extractors are only called if set before
            if extract_option and (
                option := self._extract_option(entity_content, option_delimiters)
            ):
                extracted_entity = option
            elif extract_comment and (
                comment := self._extract_comment(entity_content, comment_prefixes)
            ):
                extracted_entity = comment
            elif extract_section and (
                section_name := self._extract_section_name(entity_content)
            ):
                extracted_entity = section_name

            # Handling section names

            if isinstance(extracted_entity, _SectionName):
                if extracted_entity in parsed_ini.sections:
                    # section already parsed. add to it.
                    current_section = parsed_ini.sections[extracted_entity]
                else:
                    # new section
                    current_section = SectionProxy(name=extracted_entity)
                    parsed_ini.sections[current_section.name] = current_section
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
                if not continuation_allowed:
                    raise IniContinuationError(
                        f"line {entity_index} is continuation but continuation is not allowed"
                    )
                if not possible_continuation:
                    raise IniContinuationError(
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
                parsed_ini.sections[current_section.name] = current_section

            # add comment or option to current section's structure
            current_section.structure.append(extracted_entity)

            if isinstance(extracted_entity, _Option):
                # add option to current section's options
                last_option = extracted_entity
                current_section.options[extracted_entity.key] = extracted_entity

        return parsed_ini

    def _process_line(
        self,
        line: str,
        comment_prefixes: tuple[str, ...],
        option_delimiters: tuple[str, ...],
        open_option: bool,
    ) -> _SectionName | _Comment | _Option | str:
        # try to extract entities or else return the input
        if not open_option:
            if section_name := self._extract_section_name(line):
                return section_name
            elif option := self._extract_option(line, option_delimiters):
                return option
        elif comment := self._extract_comment(line, comment_prefixes):
            return comment
        return line

    def _extract_section_name(self, line: str) -> _SectionName | None:
        section = search(r"(?<=^\[).*(?=\]$)", line)
        return _SectionName(section.group(0).strip()) if section else None

    def _extract_comment(
        self, line: str, comment_prefixes: tuple[str, ...]
    ) -> _Comment | None:
        comment = split(
            rf"(?<=^[{''.join(escape(comment_prefix) for comment_prefix in comment_prefixes)}])(?=.)",
            line,
            maxsplit=1,
        )
        if len(comment) != 2:
            return None
        return _Comment(content=comment[-1].strip(), delimiter=comment[0].strip())

    def _extract_option(self, line: str, delimiters: tuple[str, ...]) -> _Option | None:
        # extracting left and right side of delimiter
        lr = split(
            rf"[{''.join(escape(delimiter) for delimiter in delimiters)}]",
            line,
            maxsplit=1,
        )

        if len(lr) != 2:
            # no split was possible (line is not option)
            return None

        key, value = lr

        key = key.strip()
        # taking last word of left side as key
        key = search(r"\b([\w\.\-\_]+)\b$", key)
        if not key:
            return None
        key = key.group(0)

        value = value.strip()

        return _Option(key=_OptionKey(key), value=value or None)

    def _init_section_metas(self, cfg: ParsedIni) -> None:
        for name, section in self._smartini_section_metas:
            setattr(self, name, section(cfg.sections[_SectionName(section._name)]))
