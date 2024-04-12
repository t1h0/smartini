"""Interface classes exist for coder interaction, to simplify the process
behind smartini."""

from typing import Any, Literal, overload
from typing_extensions import Self
import itertools
import re
from pathlib import Path
from dataclasses import replace as dataclass_replace
from src.exceptions import (
    ContinuationError,
    IniStructureError,
    ExtractionError,
)
from src.entities import Comment, Option, SectionName, UndefinedOption, Slot
from src.args import Parameters
from src.globals import (
    COMMENT_VAR_PREFIX,
    UNNAMED_SECTION_NAME,
    SECTION_NAME_VARIABLE,
    INTERNAL_PREFIX,
    INTERNAL_PREFIX_IN_WORDS,
)
from src.utils import _str_to_var
from nomopytools.func import copy_doc


class _SectionMeta(type):
    """Metaclass for ini configuration file sections. Section names must be specified
    via '__name' class variable.
    """

    # name of the section. must be provided!
    _name: str | None

    def __new__(cls, __name: str, __bases: tuple, __dict: dict):
        #  make sure it's the initialization call
        if (
            __bases
            and Section in __bases
            and __name != "UndefinedSection"
            and SECTION_NAME_VARIABLE not in __dict
        ):
            raise AttributeError(
                f"Class '{__name}' must define section name as '{SECTION_NAME_VARIABLE}' class attribute."
            )
        return super().__new__(cls, __name, __bases, __dict)


class Section(metaclass=_SectionMeta):

    # name of the section. must be provided!
    _name: str | None

    def __init__(self) -> None:
        """An ini configuration file section. Name of the section must be defined via
        '__name' class attribute.
        """
        # initialize Options
        for var, val in vars(self.__class__).items():
            # every string variable without leading INTERNAL_PREFIX
            # will be interpreted as an option
            if (
                not re.fullmatch(r"^__.*__$", var)
                and isinstance(val, str)
                and var != SECTION_NAME_VARIABLE
            ):
                if var.startswith(INTERNAL_PREFIX):
                    raise NameError(
                        f"Option variable names must not start with "
                        f"{INTERNAL_PREFIX_IN_WORDS} (for '{var}')."
                    )
                setattr(self, var, Option(key=val))

    def __getattribute__(self, __name: str) -> Any:
        attr = super().__getattribute__(__name)
        return attr.value if isinstance(attr, Option) else attr

    @overload
    def _get_option(self, name: str = ..., key: ... = ...) -> ...: ...

    @overload
    def _get_option(self, name: None = ..., key: str = ...) -> ...: ...

    def _get_option(self, name: str | None = None, key: str | None = None) -> Option:
        """Get an option by variable name or option key.

        Args:
            name (str | None, optional): Name of the option variable. Defaults to None.
            key (str | None, optional): The option key. Defaults to None.
        Returns:
            Option: The requested option.
        """
        if name is not None:
            attr = super().__getattribute__(name)
            if not isinstance(attr, Option):
                raise ValueError(
                    f"{name} is no known option of section '{getattr(self,SECTION_NAME_VARIABLE)}'."
                )
            return attr
        elif key is not None:
            option = next(
                (
                    val
                    for val in vars(self).values()
                    if isinstance(val, Option) and val.key == key
                ),
                None,
            )
            if option is None:
                raise NameError(
                    f"'{key}' is not a known key of any option in section '{getattr(self,SECTION_NAME_VARIABLE)}'"
                )
            return option
        raise ValueError("name or key must be provided.")

    @overload
    def _set_option(
        self,
        name: str,
        value: ...,
        slot: ... = ...,
        key: ... = ...,
    ) -> None: ...
    @overload
    def _set_option(
        self,
        name: None,
        value: ...,
        slot: ... = ...,
        key: str = ...,
    ) -> None: ...

    def _set_option(
        self,
        name: str | None,
        value: str,
        slot: Slot = "auto",
        key: str | None = None,
    ) -> None:
        """Set an option's value by accessing it via variable name or option key.

        Args:
            name (str | None): The variable name of the option. Must be None if key
                should be used.
            value (str): The value to set the option to.
            slot ("auto", "base", "user", optional): The slot to use. If "auto" will use
                default Option behaviour. Defaults to "auto".
            key (str | None, optional): The option key. Defaults to None.
        """
        option = self._get_option(name, key)
        option.set_value(value, slot)

    def _add_undefined_option(
        self, option: UndefinedOption | Option | None = None, **option_kwargs
    ) -> UndefinedOption:
        """Add a new undefined option to the section.

        Args:
            option (UndefinedOption | Option | None, optional): The option to add.
                Has to be None if kwargs should be used. Defaults to None.
            **option_kwargs: Keyword arguments for option initialization.

        Returns:
            UndefinedOption: The newly created undefined option.
        """
        if not option:
            option = UndefinedOption(**option_kwargs)
        elif isinstance(option, Option):
            option = UndefinedOption(option)
        option_varname = _str_to_var(option.key)
        # add undefined option to section
        setattr(self, option_varname, option)
        return option

    def _add_comment(self, comment: Comment | None = None, **comment_kwargs) -> Comment:
        """Add a new comment to the section.

        Args:
            comment (Comment | None, optional): The comment to add. Must be None if
                kwargs should be used. Defaults to None.
            **comment_kwargs: Keyword arguments for Comment initialization.

        Returns:
            Comment: The newly added comment.
        """
        if not comment:
            comment = Comment(**comment_kwargs)
        setattr(
            self,
            self._get_next_comment_var(),
            comment,
        )
        return comment

    def _get_next_comment_var(self) -> str:
        """Get the variable name for the next comment.

        Returns:
            str: The variable name of the next comment.
        """
        comment_ids = sorted(
            int(cid[0])
            for var, val in vars(self).items()
            if isinstance(val, Comment)
            and (cid := re.search(rf"(?<=^{COMMENT_VAR_PREFIX})\d+$", var))
        )
        return str(comment_ids[-1] + 1 if comment_ids else 0)


class UndefinedSection(Section):
    def __init__(self, section_name: str | None) -> None:
        """Class for sections that are not user-defined in the provided schema.

        Args:
            section_name (str | None): Name of the section.
        """
        setattr(self, SECTION_NAME_VARIABLE, section_name)
        super().__init__()


class _SchemaMeta(type):
    """Metaclass for schema class."""

    def __new__(cls, __name: str, __bases: tuple, __dict: dict):
        #  make sure it's the initialization call
        if __bases and Schema in __bases:
            if wrong_var := next(
                (
                    var
                    for var, val in __dict.items()
                    if isinstance(val, _SectionMeta) and var.startswith(INTERNAL_PREFIX)
                ),
                None,
            ):
                raise NameError(
                    "Section variable names must not start with "
                    f"{INTERNAL_PREFIX_IN_WORDS} (for '{__dict['__qualname__']}."
                    f"{wrong_var}')"
                )
        return super().__new__(cls, __name, __bases, __dict)


class Schema(metaclass=_SchemaMeta):

    def __init__(self, parameters: Parameters | None = None, **kwargs) -> None:
        """Schema class. Parameters will be stored as default read and write parameters.

        Args:
            parameters (Parameters | None, optional): Default parameters for reading and
                writing inis, as an Parameters object. Parameters can also be passed
                as kwargs. Missing parameters (because parameters is None and no or not
                enough kwargs are passed) will be taken from default Parameters
                (see doc of Parameters). Defaults to None.
            **kwargs (optional): Parameters as kwargs. See doc of Parameters for details.
        """

        ### read arguments ###
        if parameters is None:
            parameters = Parameters()
        if kwargs:
            parameters = dataclass_replace(parameters, **kwargs)
        self._default_parameters = parameters

    @property
    def _user(self) -> Self:
        """Gives access to option values in the user slot."""
        return SlotProxy(target=self, slot="user")

    @property
    def user(self) -> Self:
        """Gives access to option values in the user slot."""
        return self._user

    @property
    def _base(self) -> Self:
        """Gives access to option values in the base slot."""
        return SlotProxy(target=self, slot="base")

    @property
    def base(self) -> Self:
        """Gives access to option values in the base slot."""
        return self._base

    def _with_slot(self, slot: Literal["base", "user"]) -> Self:
        """Access the ini using a specific slot.

        Args:
            slot ("base" | "user"): The slot to use.
        """
        return getattr(self, slot)

    @copy_doc(_with_slot)
    def with_slot(self, *args, **kwargs) -> ...:
        return self._with_slot(*args, **kwargs)

    def _get_sections(self) -> dict[str, Section]:
        """Get all sections of the ini.

        Returns:
            dict[str, Section]: Dicitonary with access (variable) names as keys and the
                Sections as values.
        """
        return {var: val for var, val in vars(self).items() if isinstance(val, Section)}

    @copy_doc(_get_sections)
    def get_sections(self, *args, **kwargs) -> ...:
        return self._get_sections(*args, **kwargs)

    def _read_ini(
        self,
        path: str | Path,
        parameters: Parameters | None = None,
        slot: Slot = "auto",
        parameters_as_default: bool = False,
        **kwargs,
    ) -> None:
        """Read an ini file. If no parameters are passed (as Parameters object or kwargs),
        default parameters defined on initialization will be used.

        Args:
            path (str | Path): Path to the ini file.
            parameters (Parameters | None, optional): Parameters for reading and
                writing inis, as an Parameters object. Parameters can also be passed
                as kwargs. Missing parameters (because parameters is None and no or not
                enough kwargs are passed) will be taken from default Parameters that
                were defined on initialization. Defaults to None.
            slot ("auto" | "base" | "user", optional): Slot to save option values in.
                If "auto", will use Option default behavior. Defaults to "auto".
            parameters_as_default (bool, optional): Whether to save the parameters for
                this read as default parameters. Defaults to False.
            **kwargs (optional): Parameters as kwargs. See doc of Parameters for details.
        """
        # define parameters
        if parameters is None:
            # take parameters from copy of self._parameters
            parameters = self._default_parameters
        if kwargs:
            parameters = dataclass_replace(parameters, **kwargs)
        if parameters_as_default:
            self._default_parameters = parameters

        with open(path, "r") as file:
            file_content = file.read()

        current_option: Option | None = None
        current_section = self._get_unnamed_section(parameters)

        # split into entities
        entities = re.split(
            parameters.entity_delimiter,
            file_content,
        )

        for entity_index, entity_content in enumerate(entities):

            entity_content, possible_continuation = (
                self._check_for_possible_continuation(
                    entity_content, current_option, parameters
                )
            )

            if self._is_empty_entity(entity_content, parameters):
                # empty entity, skip and close off last option
                current_option = None
                continue

            # try to extract section
            if (
                not possible_continuation
                or "section" not in parameters.continuation_ignore
            ):
                if extracted_section_name := self._extract_section_name(entity_content):
                    current_section = self._handle_section_name(
                        extracted_section_name, parameters
                    )
                    continue

            if current_section is None:
                # we need a current section to extract options and comments
                continue

            # try to extract option
            if (
                not possible_continuation
                or "option" not in parameters.continuation_ignore
            ):
                if option := self._extract_option(entity_content, parameters):
                    if handled_option := self._handle_option(
                        option, parameters, current_section, slot
                    ):
                        current_option = handled_option
                        continue

            # try to extract comment
            if (
                not possible_continuation
                or "comment" not in parameters.continuation_ignore
            ):
                if comment := self._extract_comment(entity_content, parameters):
                    self._handle_comment(comment, current_section)
                    continue

            # possible continuation
            if not current_option:
                # no last option (e.g. empty line after the last one)
                raise IniStructureError(
                    f"line {entity_index} could not be assigned to a key."
                )
            if not parameters.continuation_allowed:
                raise ContinuationError(
                    f"line {entity_index} is continuation but continuation is not allowed."
                )
            if not possible_continuation:
                raise ContinuationError(
                    f"line {entity_index} doesn't follow continuation rules."
                )
            self._handle_continuation(entity_content, current_option)

    @copy_doc(_read_ini)
    def read_ini(self, *args, **kwargs) -> ...:
        return self._read_ini(*args, **kwargs)

    def _check_for_possible_continuation(
        self, entity: str, current_option: Option | None, parameters: Parameters
    ) -> tuple[str, bool]:
        """Check if entity is a possible continuation and remove the continuation prefix
        from the entity.

        Args:
            entity (str): The entity to check.
            current_option (Option | None): The current option.
            parameters (Parameters): Ini read and write parameters.

        Returns:
            tuple[str, bool]: The entity with the continuation prefix removed (if
            possible continuation) and a boolean indicating if the entity is a possible
            continuation.
        """
        continuation = None
        if parameters.continuation_allowed and current_option:
            # if no last option it can't be a continuation
            continuation = self._extract_continuation(entity, parameters)
        is_continuation = continuation is not None
        return (continuation if is_continuation else entity, is_continuation)

    def _extract_section_name(self, entity: str) -> SectionName | None:
        """Extract a section name if present in entity.

        Args:
            entity (str): The entity to extract the section from.

        Returns:
            SectionName | None: The extracted section name or None if no section name
                was found in entity.
        """
        try:
            return SectionName(name_with_brackets=entity)
        except ExtractionError:
            return None

    def _handle_section_name(
        self, extracted_section_name: SectionName, parameters: Parameters
    ) -> Section | None:
        """Handle an extracted SectionName (add new section if necessary).

        Args:
            section_name (SectionName): The extracted section name.
            parameters (Parameters): Ini read and write parameters.

        Returns:
            Section | None: The section belonging to the extracted SectionName or None
                if no section belongs to it (i.e. no section could be created because
                of Parameters).
        """

        # check if Section exists in schema
        section_var, section = next(
            (
                (var, val)
                for var, val in itertools.chain(
                    vars(self).items(), vars(self.__class__).items()
                )
                if isinstance(val, (Section, _SectionMeta))
                and getattr(val, SECTION_NAME_VARIABLE) == extracted_section_name
            ),
            (None, None),
        )
        if section_var and section:
            if isinstance(section, _SectionMeta):
                # section is defined but not yet initialized. do so.
                section = section()
                setattr(self, section_var, section)
        elif parameters.read_undefined in (True, "section"):
            # undefined section
            valid_varname = _str_to_var(extracted_section_name)
            section = UndefinedSection(extracted_section_name)
            setattr(self, valid_varname, section)
        else:
            # section is not defined and undefined sections are not allowed, thus
            section = None

        return section

    def _extract_option(self, entity: str, parameters: Parameters) -> Option | None:
        """Extract an option if present in entity.

        Args:
            entity (str): The entity to extract the section from.
            parameters (Parameters): Ini read and write parameters.
            section (Section): The section to add the option to.

        Returns:
            Option | None: The extracted option or None if no option was found in entity.
        """
        try:
            return Option(delimiter=parameters.option_delimiters, from_string=entity)
        except ExtractionError:
            return None

    def _handle_option(
        self,
        extracted_option: Option,
        parameters: Parameters,
        section: Section,
        slot: Slot = "auto",
    ) -> Option | None:
        """Handle an extracted Option.

        Args:
            extracted_option (Option): Extracted option to handle.
            parameters (Parameters): Ini read and write parameters.
            section (Section): The section to add the option to.
            slot ("auto" | "base" | "user", optional): Slot to save the option value in.
                If "auto", will use Option default behavior. Defaults to "auto".

        Returns:
            Option | None: The final Option in the section (differs from input) or None
                if Option could not be handled (e.g. due to undefined and undefined not
                allowed in parameters).
        """
        # check if Option is defined
        try:
            option = section._get_option(key=extracted_option.key)
        except NameError:
            if parameters.read_undefined in (True, "option"):
                # create UndefinedOption
                option = section._add_undefined_option(
                    key=extracted_option.key, delimiter=extracted_option.delimiter
                )
            else:
                return None

        # set option value
        option.set_value(extracted_option.value, slot)

        return option

    def _extract_comment(self, entity: str, parameters: Parameters) -> Comment | None:
        """Extract an comment if present in entity.

        Args:
            entity (str): The entity to extract the section from.
            parameters (Parameters): Ini read and write parameters.

        Returns:
            Comment | None: The extracted comment or None if no comment
                was found in entity.
        """
        try:
            return Comment(
                prefix=parameters.comment_prefixes, content_with_prefix=entity
            )
        except ExtractionError:
            return None

    def _handle_comment(self, extracted_comment: Comment, section: Section) -> None:
        """Handle an extracted Comment (add it to a section).

        Args:
            extracted_comment (Comment): Extracted comment to handle.
            section (Section): The section to add the comment to.

        """
        section._add_comment(extracted_comment)

    def _extract_continuation(self, entity: str, parameters: Parameters) -> str | None:
        """Extract a possible continuation from an entity.

        Args:
            entity (str): The entity.
            parameters (Parameters): Ini read and write parameters.

        Returns:
            str: The continuation or None if continuation was not found.
        """
        continuation = re.search(rf"(?<=^{parameters.continuation_prefix}).*", entity)
        return None if continuation is None else continuation[0]

    def _handle_continuation(self, continuation: str, last_option: Option) -> None:
        """Handles a continutation (adds it to the last option).

        Args:
            continuation (str): The continuation.
            last_option (Option): The last option to add the continuation to.
        """
        # add continuation to last option
        if not isinstance(last_option.value, list):
            last_option.value = [last_option.value]
        last_option.value.append(continuation)

    def _get_unnamed_section(self, parameters: Parameters) -> Section | None:
        """Get the unnamed section (always at the beginning of the ini).

        Args:
            parameters (Parameters): Ini read and write parameters.

        Returns:
            Section | None: The unnamed section or None if unnamed section undefinied
                and not allowed.
        """
        # check if unnamed section is in schema else create UndefinedSection
        varname, schema = next(
            (
                (var, val)
                for var, val in vars(self.__class__).items()
                if isinstance(val, _SectionMeta)
                and getattr(val, SECTION_NAME_VARIABLE) is None
            ),
            (None, None),
        )
        if varname and schema:
            section = schema()
            setattr(self, varname, section)
        elif parameters.read_undefined in (True, "section"):
            section = UndefinedSection(section_name=None)
            setattr(self, UNNAMED_SECTION_NAME, section)
        else:
            section = None

        return section

    def _is_empty_entity(self, entity: str, parameters: Parameters) -> bool:
        """Check whether an entity qualifies as empty.

        Args:
            entity (str): The entity to check.
            parameters (Parameters): Ini read and write parameters.

        Returns:
            bool: Whether the entity is empty.
        """
        return bool(
            re.fullmatch(
                r"[\s\t]*" if parameters.ignore_whitespace_lines else r"", entity
            )
        )


class SlotProxy:

    def __init__(
        self,
        target: Schema | Section,
        slot: Literal["base", "user"],
    ) -> None:
        """Gives access to a specific slot.

        Args:
            target (Schema | Section): The target to prepare for slot access.
            slot ("base", "user"): The slot to access.
        """
        super().__setattr__("_target", target)
        super().__setattr__("_slot", slot)

    def __getattribute__(self, name: str) -> Any:
        target = super().__getattribute__("_target")
        slot = super().__getattribute__("_slot")
        if isinstance(target, Schema):
            return SlotProxy(target=getattr(target, name), slot=slot)
        elif isinstance(target, Section):
            return target._get_option(name).get_value(slot)

    def __setattr__(self, name: str, value: Any) -> None:
        target = super().__getattribute__("_target")
        slot = super().__getattribute__("_slot")
        if not isinstance(target, Section):
            raise AttributeError("Assignment only valid for options.")
        target._set_option(name=name, value=value, slot=slot)
