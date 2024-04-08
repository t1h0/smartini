"""Interface classes exist for coder interaction, to simplify the process
behind smartini."""

from pathlib import Path
from dataclasses import replace as dataclass_replace
import contextlib
from typing import Any, Literal, overload, Callable
from src.exceptions import (
    ContinuationError,
    IniStructureError,
    ExtractionError,
    UndefinedSectionError,
)
from src.entities import Comment, Option, SectionName, UndefinedOption
from src.args import Parameters
from src.globals import (
    COMMENT_VAR_PREFIX,
    UNNAMED_SECTION_NAME,
    SECTION_NAME_VARIABLE,
    INTERNAL_PREFIX,
    INTERNAL_PREFIX_IN_WORDS,
    VARIABLE_PREFIX,
)
from re import search, split, fullmatch, sub
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
                not fullmatch(r"^__.*__$", var)
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


            )
            if var is None:
                raise NameError(
                    f"'{key}' is not a known key of any option in section '{getattr(self,SECTION_NAME_VARIABLE)}'"
                )
            option = var
        match cfg:
            case "auto":
                setattr(self, option, value)
            case "base":
                super().__getattribute__(option)


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

        empty_entity = r"[\s\t]*" if parameters.ignore_whitespace_lines else r""

        with open(path, "r") as file:
            file_content = file.read()

        current_option: Option | None = None
        current_section = self._get_unnamed_section(parameters)

        # split into entities
        entities = split(
            parameters.entity_delimiter,
            file_content,
        )

        for entity_index, entity_content in enumerate(entities):

            if possible_continuation := (
                self._check_for_possible_continuation(
                    entity_content, current_option, parameters
                )
            ):
                entity_content = possible_continuation
            possible_continuation = False if possible_continuation is None else True

            if fullmatch(empty_entity, entity_content):
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
                # we need a last section to extract options and comments
                continue

            extracted_entity = self._extract_option_comment(
                entity_content, current_section, possible_continuation, parameters
            )

            if isinstance(extracted_entity, Option):
                current_option = extracted_entity
            elif not extracted_entity:
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
    ) -> str | None:
        """Check if entity is a possible continuation and remove the continuation prefix
        from the entity.

        Args:
            entity (str): The entity to check.
            current_option (Option | None): The current option.
            parameters (Parameters): Ini read and write parameters.

        Returns:
            str | None: The entity with the continuation prefix removed (if
            possible continuation) or None if entity is no possible continuation.
        """
        if parameters.continuation_allowed and current_option:
            # if no last option it can't be a continuation
            if continuation := self._extract_continuation(entity, parameters):
                return continuation
        return None

    def _extract_option_comment(
        self,
        entity: str,
        current_section: Section | None,
        possible_continuation: bool,
        parameters: Parameters,
    ) -> Option | Comment | None:
        """Extract Option or Comment from entity.

        Args:
            entity (str): Entity to use for extraction.
            current_section (Section | None): Current section.
            possible_continuation (bool): Whether entity is possible continuation.
            parameters (Parameters): Ini read and write parameters.

        Returns:
            Option | Comment | None: Option if option present in entity, Comment if
                comment present, None if neither.
        """
        # get extractors
        extractors = {
            "option": self._extract_and_add_option,
            "comment": self._extract_and_add_comment,
        }
        if possible_continuation:
            extractors = {
                k: v
                for k, v in extractors.items()
                if k not in parameters.continuation_ignore
            }
        # extract
        for Extractor in extractors.values():
            with contextlib.suppress(ExtractionError):
                return Extractor(
                    entity=entity,
                    parameters=parameters,
                    section=current_section,
                )
        return None

    def _extract_section_name(self, entity: str) -> SectionName | None:
        """Extract a section name if present in entity.

        Args:
            entity (str): The entity to extract the section from.

        Returns:
            SectionName | None: The extracted section name or None if extraction
                wasn't possible.
        """
        try:
            return SectionName(name_with_brackets=entity)
        except ExtractionError:
            return None

    def _handle_section_name(
        self, extracted_section_name: SectionName, parameters: Parameters
    ) -> Section | None:
        """Handle a SectionName (add new section if necessary).

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
                for var, val in vars(self.__class__).items()
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
            valid_varname = self._str_to_var(extracted_section_name)
            section = UndefinedSection(extracted_section_name)
            setattr(self, valid_varname, section)
        else:
            # section is not defined and undefined sections are not allowed, thus
            section = None

        return section

    def _extract_and_add_option(
        self, entity: str, parameters: Parameters, section: Section
    ) -> Option:
        """Extract an option if present in entity and add it if necessary.

        Args:
            entity (str): The entity to extract the section from.
            parameters (Parameters): Ini read and write parameters.
            section (Section): The section to add the option to.

        Raises:
            ExtractionError: If no option present in entity.

        Returns:
            Option: The extracted option.
        """
        try:
            extracted_option = Option(
                delimiter=parameters.option_delimiters, from_string=entity
            )
        except ExtractionError as e:
            raise ExtractionError from e

        # check if Option is defined
        if option := next(
            (
                val
                for val in vars(section).values()
                if isinstance(val, Option) and val.key == extracted_option.key
            ),
            None,
        ):
            option.value = extracted_option.value
            return option
        elif parameters.read_undefined in (True, "option"):
            # create UndefinedOption
            option = UndefinedOption(extracted_option)
            option_varname = self._str_to_var(option.key)
            setattr(section, option_varname, option)
        else:
            raise ExtractionError(
                f"Option '{extracted_option.key}' is undefined but undefined options are not allowed."
            )

        return option

    def _extract_and_add_comment(
        self, entity: str, parameters: Parameters, section: Section
    ) -> Comment:
        """Extract an comment if present in entity and add it if necessary.

        Args:
            entity (str): The entity to extract the section from.
            parameters (Parameters): Ini read and write parameters.
            section (Section): The section to add the comment to.

        Raises:
            ExtractionError: If no comment present in entity.

        Returns:
            Comment: The extracted comment.
        """
        try:
            extracted_comment = Comment(
                prefix=parameters.comment_prefixes, content_with_prefix=entity
            )
        except ExtractionError as e:
            raise ExtractionError from e

        setattr(
            section,
            self._get_next_comment_var(section),
            extracted_comment,
        )

        return extracted_comment

    def _extract_continuation(self, entity: str, parameters: Parameters) -> str | None:
        """Extract a possible continuation from an entity.

        Args:
            entity (str): The entity.
            parameters (Parameters): Read and write ini parameters.

        Returns:
            str: The continuation or None if continuation was not found.
        """
        continuation = search(rf"(?<=^{parameters.continuation_prefix}).*", entity)
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

    def _get_next_comment_var(self, section: Section) -> str:
        """Get the variable name for the next comment.

        Args:
            section (Section): The section the comment belongs to.

        Returns:
            str: The variable name of the next comment.
        """
        comment_ids = sorted(
            int(cid[0])
            for var, val in vars(section).items()
            if isinstance(val, Comment)
            and (cid := search(rf"(?<=^{COMMENT_VAR_PREFIX})\d+$", var))
        )
        return str(comment_ids[-1] + 1 if comment_ids else 0)

    def _str_to_var(self, string: str) -> str:
        """Convert a string to a valid python variable name.

        Args:
            string (str): The string to convert.

        Returns:
            str: The valid variable name.
        """
        return sub(
            rf"^(?=\d|{INTERNAL_PREFIX})", VARIABLE_PREFIX, sub(r"\W", "_", string)
        )
