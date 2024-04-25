"""Interface classes exist for coder interaction, to simplify the process
behind smartini."""

from typing import Any, Literal, overload, Sequence, Self, Callable
import itertools
import re
from pathlib import Path
from dataclasses import replace as dataclass_replace
from src.exceptions import (
    ContinuationError,
    IniStructureError,
    ExtractionError,
    EntityNotFound,
    SlotNotFound,
)
from src.entities import Comment, Option, SectionName, UndefinedOption
from src import slots
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
import warnings
import inspect

class SectionMeta(type):
    """Metaclass for ini configuration file sections. Section names must be specified
    via '_name' class variable.
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


class Section(metaclass=SectionMeta):

    # name of the section. must be provided!
    _name: str | None

    Structure = list[Option | Comment]

    def __init__(self) -> None:
        """An ini configuration file section. Name of the section must be defined via
        '_name' class attribute.
        """
        # schema_structure contains the initial structure as saved in the schema
        self._schema_structure: Section.Structure = []
        # slots contain a structure each containing the order of options and comments
        self._slots: slots.Slots[Section.Structure] = []

        # initialize Options
        for var, val in vars(self.__class__).items():
            # every string variable without leading and trailing doublescores
            # will be interpreted as an option
            if (
                not re.fullmatch(r"^__.*__$", var)
                and isinstance(val, str)
                and var != SECTION_NAME_VARIABLE
            ):
                if var.startswith(INTERNAL_PREFIX):
                    raise NameError(
                        f"'{var}' is interpreted as an Option but Option variable names "
                        f"must not start with {INTERNAL_PREFIX_IN_WORDS}."
                    )
                option = Option(key=val)
                super().__setattr__(var, option)
                self._schema_structure.append(option)

    @property
    def _nslot(self) -> int:
        return len(self._slots)

    @property
    def nslot(self) -> int:
        return self._nslot

    def __setattr__(self, name: str, value: Any) -> None:
        if isinstance(value, (Option, Comment)):
            raise ValueError(
                "Options and Comments must be added using the respective methods."
            )
        super().__setattr__(name, value)

    def _add_slots(self, n: int = 1) -> None:
        self._slots.extend([] for _ in range(n))

    @overload
    def _get_option(self, name: str = ..., key: ... = ...) -> Option: ...

    @overload
    def _get_option(self, name: None = ..., key: str = ...) -> Option: ...

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
                raise EntityNotFound(
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
                raise EntityNotFound(
                    f"'{key}' is not a known key of any option in section '{getattr(self,SECTION_NAME_VARIABLE)}'"
                )
            return option
        raise ValueError("name or key must be provided.")

    @copy_doc(_get_option)
    def get_option(self, *args, **kwargs) -> ...:
        return self._get_option(*args, **kwargs)

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
        slot: slots.SlotAccess = -1,
        key: str | None = None,
    ) -> None:
        """Set an option's value by accessing it via variable name or option key.

        Args:
            name (str | None): The variable name of the option. Must be None if key
                should be used.
            value (str): The value to set the option to.
            slot (int | list[int] | None, optional): The slot to use. Either
                int for the specific slot or list of slots or None for all slots.
                Defaults to -1 (latest slot).
            key (str | None, optional): The option key. Defaults to None.
        """
        if key is None:
            if name is None:
                raise ValueError("Need name or key for option setting.")
        elif name is not None:
            warnings.warn("Key passed but name is not None. Taking name instead.")
        option: Option = self._get_option(name, key)
        option.set_value(value, slot)

    @copy_doc(_set_option)
    def set_option(self, *args, **kwargs) -> ...:
        return self._set_option(*args, **kwargs)

    @overload
    def _add_entity(
        self,
        entity: ...,
        position: int = ...,
        slot: slots.SlotAccess = ...,
    ) -> ...: ...

    @overload
    def _add_entity(
        self,
        entity: ...,
        position: list[int] = ...,
        slot: int | list[int] = ...,
    ) -> ...: ...

    @overload
    def _add_entity(
        self,
        entity: UndefinedOption | Option,
        position: ... = ...,
        slot: ... = ...,
    ) -> UndefinedOption: ...

    @overload
    def _add_entity(
        self,
        entity: Comment,
        position: ... = ...,
        slot: ... = ...,
    ) -> Comment: ...

    def _add_entity(
        self,
        entity: UndefinedOption | Option | Comment,
        position: int | list[int] = -1,
        slot: slots.SlotAccess = None,
        add_missing_slots=True,
    ) -> UndefinedOption | Comment:
        """Add a new entity to the section.

        Args:
            entity (UndefinedOption | Option | Comment): The entity to add.
            position (int | list[int | None], optional): Where to put the entity in
                the section's structure. Either a list with one position per slot
                or int for same position in all slots. Defaults to -1 (append to end in
                every slot).
            slot (int | list[int] | None, optional): Slot(s) to add the entity to.
                Either int for one slot, list of int for multiple slots or None for all
                slots. Must fit to position. Defaults to None.
            add_missing_slots (bool, optional): Whether to add missing slots if slot
                doesn't exist yet. Defaults to True.

        Returns:
            UndefinedOption | Comment: The newly created entity.
        """
        if isinstance(entity, Option):
            if not isinstance(entity, UndefinedOption):
                entity = UndefinedOption(entity)
            varname = _str_to_var(entity.key)
        elif isinstance(entity, Comment):
            varname = self._get_next_comment_var()
        else:
            raise ValueError("Can only add (Undefined)Options or Comments.")

        # add entity to section
        super().__setattr__(varname, entity)

        # add to structure
        slot = self._get_slot_access(slot)
        if isinstance(position, int):
            position = [position]
        if len(position) != len(slot):
            raise ValueError("Number of positions must match number of slots.")
        # for faster adding of missing slots we'll go from highest slot to lowest
        for s, pos in sorted(zip(slot, position), reverse=True):
            if not -self._nslot <= s < self._nslot:
                if s >= 0 and add_missing_slots:
                    self._add_slots(s - self._nslot + 1)
                else:
                    raise SlotNotFound(
                        f"Can't insert into slot {s} because it doesn't exist."
                    )
            if not -len(self._slots[s]) - 1 <= pos <= len(self._slots[s]):
                raise IndexError(
                    f"Can't insert into slot {s} at position {pos} because slot is too small."
                )
            self._slots[s].insert(pos, entity)
        return entity

    @copy_doc(_add_entity)
    def add_entity(self, *args, **kwargs) -> ...:
        return self._add_entity(*args, **kwargs)

    def _get_options(self) -> dict[str, Option]:
        """Get all options of the section.

        Returns:
            dict[str, Option]: Variable names as keys and Options as values.
        """
        return {
            name: var for name, var in vars(self).items() if isinstance(var, Option)
        }

    @copy_doc(_get_options)
    def get_options(self, *args, **kwargs) -> ...:
        return self._get_options(*args, **kwargs)

    def _get_comments(self) -> tuple[tuple[str, Comment], ...]:
        """Get all comments of the section.

        Returns:
            tuple[tuple[str, Comment],...]: Tuples of variable Name and Comment.
        """
        return tuple(
            (name, var) for name, var in vars(self).items() if isinstance(var, Comment)
        )

    @copy_doc(_get_comments)
    def get_comments(self, *args, **kwargs) -> ...:
        return self._get_comments(*args, **kwargs)

    def _get_next_comment_var(self) -> str:
        """Get the variable name for the next comment.

        Returns:
            str: The variable name of the next comment.
        """
        comment_ids = tuple(
            int(cid[0])
            for name, _ in self._get_comments()
            if (cid := re.search(rf"(?<=^{COMMENT_VAR_PREFIX})\d+$", name))
        )
        return COMMENT_VAR_PREFIX + str(comment_ids[-1] + 1 if comment_ids else 0)

    def _set_structure(
        self, new_structure: Sequence[Option | Comment] | Sequence, slot: slots.SlotAccess
    ) -> None:
        slot = self._get_slot_access(slot)
        if any(entity not in vars(self).values() for entity in new_structure):
            raise IniStructureError(
                "Entities of new structure must all belong to section."
            )
        for s in slot:
            self._slots[s] = Section.Structure(new_structure)

    def _get_slot_access(self, slot: slots.SlotAccess) -> list[int]:
        if slot is None:
            return list(range(len(self._slots)))
        elif isinstance(slot, int):
            return [slot]
        for s in slot:
            if s >= self._nslot:
                raise SlotNotFound(f"Can't access slot {s} because it doesn't exist.")
        return slot


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
                    if isinstance(val, SectionMeta) and var.startswith(INTERNAL_PREFIX)
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

    def __init__(
        self,
        parameters: Parameters | None = None,
        slot_decider: slots.DeciderMethods = "default",
        **kwargs,
    ) -> None:
        """Schema class. Parameters will be stored as default read and write parameters.

        Args:
            parameters (Parameters | None, optional): Default parameters for reading and
                writing inis, as an Parameters object. Parameters can also be passed
                as kwargs. Missing parameters (because parameters is None and no or not
                enough kwargs are passed) will be taken from default Parameters
                (see doc of Parameters). Defaults to None.
            slot_decider ("default" | "latest", optional): Method to choose the slot.
                "default" will use slot 0 whenenver latest slot is None, "latest" will
                use latest slot only. Defaults to "default".
            **kwargs (optional): Parameters as kwargs. See doc of Parameters for details.
        """

        ### read arguments ###
        if parameters is None:
            parameters = Parameters()
        if kwargs:
            parameters = dataclass_replace(parameters, **kwargs)
        self._default_parameters = parameters
        self._decider_method = slot_decider
        # contains one SlotView per section
        # proxies are added on access (see __getattribute__)
        self._slot_views = {}

    @property
    def _nslot(self) -> int:
        sections = self._get_sections(filled_only=True).values()
        return max(sec._nslot for sec in sections) if sections else 0

    @property
    def nslot(self) -> int:
        return self._nslot

    def __getattribute__(self, name: str) -> Any:
        attr = super().__getattribute__(name)
        if isinstance(attr, Section):
            if name not in self._slot_views:
                self._slot_views[name] = SlotView(
                    target=attr, slot=self._decider_method
                )
            return self._slot_views[name]
        return attr

    @overload
    def __getitem__(self, key: str) -> Section: ...

    @overload
    def __getitem__(self, key: int) -> Self: ...

    def __getitem__(self, key: str | int) -> Section | Self:
        if isinstance(key, int):
            if key >= self._nslot:
                raise IndexError("Slot index out of range")
            return SlotView(target=self, slot=key)

        for _, sec in self._get_sections().items():
            if getattr(sec, SECTION_NAME_VARIABLE) == key:
                return sec
        raise EntityNotFound(f"'{key} is not a known section name.")

    def _with_slot(self, slot: int) -> Self:
        """Access the ini using a specific slot.

        Args:
            slot (int): The slot to use.
        """
        return self[slot]

    @copy_doc(_with_slot)
    def with_slot(self, *args, **kwargs) -> ...:
        return self._with_slot(*args, **kwargs)

    def _get_section(
        self, section_name: SectionName | str | None, filled_only: bool = True
    ) -> tuple[str, Section | SectionMeta]:
        if filled_only:
            iterator = vars(self).items()
            instances = Section
        else:
            iterator = itertools.chain(vars(self).items(), vars(self.__class__).items())
            instances = (Section, SectionMeta)
        try:
            return next(
                (var, val)
                for var, val in iterator
                if isinstance(val, instances)
                and getattr(val, SECTION_NAME_VARIABLE) == section_name
            )
        except StopIteration as e:
            raise EntityNotFound(
                f"Can't get section '{section_name}' because it doesn't exist."
            ) from e

    @overload
    def _get_sections(self, filled_only: Literal[True] = ...) -> dict[str, Section]: ...

    @overload
    def _get_sections(
        self, filled_only: Literal[False] = ...
    ) -> dict[str, Section | SectionMeta]: ...

    def _get_sections(
        self, filled_only: bool = True
    ) -> dict[str, Section] | dict[str, Section | SectionMeta]:
        """Get all sections of the ini.

        Args:
            filled_only (bool, optional): Whether to only return sections that have
                been filled with content already. Defaults to True.

        Returns:
            dict[str, Section] | dict[str, Section | SectionMeta]: Dicitonary with
                access (variable) names as keys and the Sections as values.
        """
        if filled_only:
            iterator = vars(self).items()
            instances = Section
        else:
            iterator = itertools.chain(vars(self).items(), vars(self.__class__).items())
            instances = (Section, SectionMeta)
        return {var: val for var, val in iterator if isinstance(val, instances)}

    @copy_doc(_get_sections)
    def get_sections(self, *args, **kwargs) -> ...:
        return self._get_sections(*args, **kwargs)

    def _read_ini(
        self,
        path: str | Path,
        parameters: Parameters | None = None,
        slot: int | None = None,
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
            slot (int | None, optional): Slot to save option values in. If None will
                create new slot. Defaults to None.
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

        if slot is not None and slot >= self._nslot:
            raise SlotNotFound(
                f"Can't read ini into slot {slot} because it doesn't exist."
            )
        slot = self._nslot if slot is None else slot

        current_option: Option | None = None
        # get unnamed section, delete later if undefined and unused
        current_section = self._get_unnamed_section(parameters=parameters)
        structure: list[Option | Comment] = []

        # split into entities
        entities = re.split(
            parameters.entity_delimiter,
            file_content,
        )

        for entity_index, entity_content in enumerate(entities):

            entity_content, possible_continuation = (
                self._check_for_possible_continuation(
                    entity_content,
                    current_option,
                    parameters,
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
                    if current_section:
                        # reorder old section structure and reset for new section
                        current_section._set_structure(
                            structure, -1 if slot is None else slot
                        )
                        structure = []
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
                        structure.append(current_option)
                        continue

            # try to extract comment
            if (
                not possible_continuation
                or "comment" not in parameters.continuation_ignore
            ):
                if comment := self._extract_comment(entity_content, parameters):
                    comment = self._handle_comment(comment, current_section, slot)
                    structure.append(comment)
                    continue

            # possible continuation
            if not current_option:
                # no option open (e.g. empty line after the last one)
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
            self._handle_continuation(entity_content, current_option, slot)

        if (
            isinstance(
                unnamed := self._get_unnamed_section(parameters), UndefinedSection
            )
            and unnamed.nslot == 0
        ):
            del unnamed

    @copy_doc(_read_ini)
    def read_ini(self, *args, **kwargs) -> ...:
        return self._read_ini(*args, **kwargs)

    def _ensure_slot_access(self, section: Section, slot: int) -> None:
        if section._nslot <= slot:
            section._add_slots(slot - section._nslot + 1)

    def _get_unnamed_section(self, parameters: Parameters) -> Section | None:
        """Get the unnamed section (always at the beginning of the ini).

        Args:
            parameters (Parameters): Ini read and write parameters.

        Returns:
            Section | None: The unnamed section or None if unnamed section undefinied
                and not allowed.
        """
        # check if unnamed section is in schema else create UndefinedSection
        try:
            varname, section = self._get_section(None, filled_only=False)
            if isinstance(section, SectionMeta):
                section = section()
                setattr(self, varname, section)
        except EntityNotFound:
            if parameters.read_undefined in (True, "section"):
                section = UndefinedSection(section_name=None)
                varname = UNNAMED_SECTION_NAME
                setattr(self, varname, section)
            else:
                section = None

        return section

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
        self,
        extracted_section_name: SectionName,
        parameters: Parameters,
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
        try:
            section_var, section = self._get_section(
                extracted_section_name, filled_only=False
            )
            if isinstance(section, SectionMeta):
                # section is defined but not yet initialized. do so.
                section = section()
                setattr(self, section_var, section)
        except EntityNotFound:
            if parameters.read_undefined in (True, "section"):
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
        slot: int,
    ) -> Option | None:
        """Handle an extracted Option.

        Args:
            extracted_option (Option): Extracted option to handle.
            parameters (Parameters): Ini read and write parameters.
            section (Section): The section to add the option to.
            slot (int): Slot to save option values in and add to the section.

        Returns:
            Option | None: The final Option in the section (differs from input) or None
                if Option could not be handled (e.g. due to undefined and undefined not
                allowed in parameters).
        """
        # check if Option is defined
        try:
            option = section._get_option(key=extracted_option.key)
            option.set_value(extracted_option.slots[0], slot, add_missing_slots=True)
        except NameError:
            if parameters.read_undefined in (True, "option"):
                new_slot = extracted_option.slots[0]
                extracted_option.set_value(None, 0)
                extracted_option.set_value(new_slot, slot, True)
                # create UndefinedOption
                option = section._add_entity(extracted_option, slot)
            else:
                return None

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

    def _handle_comment(
        self, extracted_comment: Comment, section: Section, slot: int
    ) -> Comment:
        """Handle an extracted Comment (add it to section if necessary).

        Args:
            extracted_comment (Comment): Extracted comment to handle.
            section (Section): The section to add the comment to.
            slot (int): Slot to add the comment to in the section.

        Returns:
            Comment: The comment added to the section
                (as of now the input Comment object).

        """
        section._add_entity(extracted_comment, position=-1, slot=slot)
        return extracted_comment

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

    def _handle_continuation(self, continuation: str, last_option: Option, slot: int) -> None:
        """Handles a continutation (adds it to the last option).

        Args:
            continuation (str): The continuation.
            last_option (Option): The last option to add the continuation to.
            slot (int): Slot to add the continuation to.
        """
        # add continuation to last option
        if not isinstance(last_option[slot].value, list):
            last_option[slot].value = [last_option[slot].value]
        last_option[slot].value.append(continuation)

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
        
class SlotView:
    # Note: SlotView should only contain underscore functions, otherwise __getattribute__
    # might fail

    def __init__(
        self,
        target: Schema | Section,
        slot: slots.DeciderMethods | int,
    ) -> None:
        """Gives access to a specific slot.

        Args:
            target (Schema | Section): The target to prepare for slot access.
            slot ("default" | "latest" | int): A decider method or the slot to access.
        """
        super().__setattr__("_target", target)
        super().__setattr__("_slot", slot)

    def __getattribute__(self, name: str) -> Any:
        try:
            # if SlotView has the attribute return it
            return super().__getattribute__(name)
        except AttributeError:
            target = super().__getattribute__("_target")
            slot = super().__getattribute__("_slot")
            attr = getattr(target, name)
            if isinstance(target, Schema) and isinstance(attr, Section):
                return SlotView(target=attr, slot=slot)
            elif isinstance(target, Section) and isinstance(attr, Option):
                return self._decide(attr)
            return attr

    def __setattr__(self, name: str, value: Any) -> None:
        target = super().__getattribute__("_target")
        slot = super().__getattribute__("_slot")
        if not isinstance(target, Section):
            raise AttributeError("Assignment only valid for options.")
        target._set_option(name=name, value=value, slot=slot)

    def _decide(self, target: Option) -> Any:
        slot = super().__getattribute__("_slot")
        match slot:
            case "default":
                slot= (
                    target.slots[-1]
                    if target.slots[-1] is not None
                    else target.slots[0]
                )
            case "lastest":
                slot = target.slots[-1]
            case _:
                if isinstance(slot,int):
                    slot = target.slots[slot]
                else:
                    raise ValueError("Slot or decider method invalid.")
        return slot.value
    

