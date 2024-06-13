"""Interface classes exist for coder interaction, to simplify the process
behind smartini."""

from typing import Any, Literal, Self, Callable
import itertools
import re
from pathlib import Path
import warnings
import inspect
import contextlib
from src.exceptions import (
    ContinuationError,
    IniStructureError,
    ExtractionError,
    EntityNotFound,
    DuplicateEntityError,
)
from src.entities import (
    Comment,
    Option,
    OptionSlot,
    SectionName,
    UndefinedOption,
)
from src.slots import (
    SlotAccess,
    SlotKey,
    SlotDeciderMethods,
    Slots,
    StructureSlotEntity,
    Structure,
)
from src.args import Parameters
from src.globals import (
    COMMENT_VAR_PREFIX,
    UNNAMED_SECTION_NAME,
    SECTION_NAME_VARIABLE,
    INTERNAL_PREFIX,
    INTERNAL_PREFIX_IN_WORDS,
)
from src.utils import _str_to_var
from src import warn
from nomopytools.func import copy_doc


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
            and StructureSlotEntity not in __bases
            and Section in __bases
            and __name != "UndefinedSection"
            and SECTION_NAME_VARIABLE not in __dict
        ):
            raise AttributeError(
                f"Class '{__name}' must define section name as '{SECTION_NAME_VARIABLE}'"
                " class attribute."
            )
        return super().__new__(cls, __name, __bases, __dict)


class Section(StructureSlotEntity[Option | Comment], metaclass=SectionMeta):

    # name of the section. must be provided!
    _name: str | None

    def __init__(self) -> None:
        """An ini configuration file section. Name of the section must be defined via
        'name' class attribute.
        """
        super().__init__()

        # schema_structure contains the initial structure as saved in the schema
        self._schema_structure = Structure()

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
                        f"'{var}' is interpreted as an Option but Option variable names"
                        f" must not start with {INTERNAL_PREFIX_IN_WORDS}."
                    )
                option = Option(key=val)
                super().__setattr__(var, option)
                self._schema_structure.append(option)

    def _add_entity(
        self,
        entity: UndefinedOption | Option | Comment,
        positions: int | list[int] = -1,
        *,
        slots: SlotAccess = None,
    ) -> UndefinedOption | Comment:
        """Add a new entity to the section.

        Args:
            entity (UndefinedOption | Option | Comment): The entity to add.
            positions (int | list[int | None], optional): Where to put the entity in
                the section's structure. Either one position for all slots or a list
                with one position per slot. Defaults to -1 (append to end in every slot).
            slots (SlotAccess, optional): Slot(s) to add the entity to.
                Must match positions. Defaults to None.

        Returns:
            UndefinedOption | Comment: The newly created entity.
        """
        if isinstance(entity, Option):

            # make sure option key doesn't exist already
            with contextlib.suppress(EntityNotFound):
                self._get_option(key=entity.key)
                raise DuplicateEntityError(
                    f"Option with key '{entity.key}' already exists."
                )

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
        self._insert_structure_items(entity, positions, slots=slots)

        return entity

    @copy_doc(_add_entity, annotations=True)
    def add_entity(self, *args, **kwargs) -> ...:
        return self._add_entity(*args, **kwargs)

    def __setattr__(self, name: str, value: Any) -> None:
        if isinstance(value, (Option, Comment)):
            raise ValueError(
                "Options and Comments must be added using the respective methods."
            )
        super().__setattr__(name, value)

    def _get_option(
        self, name: str | None = None, key: SlotKey | None = None
    ) -> Option:
        """Get an option by variable name or option key.

        Args:
            name (str | None, optional): Name of the option variable. Defaults to None.
            key (SlotKey | None, optional): The option key. Defaults to None.
        Returns:
            Option: The requested option.
        """
        if name is not None:
            attr = super().__getattribute__(name)
            if not isinstance(attr, Option):
                raise EntityNotFound(
                    f"{name} is no known option of section"
                    f" '{getattr(self,SECTION_NAME_VARIABLE)}'."
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
                    f"'{key}' is not a known key of any option in section"
                    f" '{getattr(self,SECTION_NAME_VARIABLE)}'"
                )
            return option
        raise ValueError("name or key must be provided.")

    @copy_doc(_get_option, annotations=True)
    def get_option(self, *args, **kwargs) -> ...:
        return self._get_option(*args, **kwargs)

    def _set_option(
        self,
        name: str | None,
        positions: int | list[int | None] | None = None,
        key: str | None = None,
        *,
        slots: SlotAccess = None,
        **kwargs,
    ) -> None:
        """Set an option's value by accessing it via variable name or option key.

        Args:
            name (str | None): The variable name of the option. Must be None if key
                should be used.
            positions (int | list[int | None] | None): Position in slots the option
                should take. Either int for same position in all slots or one position
                per slot. If None and for every slot that None is specified as the
                position, will take previous position of the Option in the respective
                slot and will append to slots where Option didn't exist before.
                Defaults to None.
            key (str | None, optional): The option key. Defaults to None.
            slots (SlotAccess, optional): The slot to use. Defaults to None (all slots).
            **kwargs: Keyword-arguments corresponding to OptionSlot attributes.
        """
        if key is None:
            if name is None:
                raise ValueError("Need name or key for option setting.")
        elif name is not None:
            warnings.warn("Key passed but name is not None. Taking name.")

        # get slots
        slots = self._slots.slot_access(slots, verify=True)

        # get option
        try:
            option: Option = self._get_option(name, key)
            # set args
            # catch manipulation warning because it doesn't apply here
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=warn.slot_manipulation)
                option._set_slots(slots=slots, add_missing_slots=True, **kwargs)
        except EntityNotFound:
            try:
                option = UndefinedOption(slots=slots, **kwargs)
            except ExtractionError as ee:
                raise ValueError(
                    "Can't add new option because of unsufficient initialization arguemnts."
                ) from ee
            option = self._add_entity(option)

        # get position
        validated_positions = self._validate_position(positions, slots)

        # make sure option is in all requested slot structures
        # and adjust positions if needed
        for slot, pos in zip(slots, validated_positions):
            structure = self._slots[slot]
            # get position of option in structure
            try:
                option_index = structure.index(option)
                if pos is not None and pos != option_index:
                    # option exists in structure but has to be moved
                    structure.insert(pos, structure.pop(option_index))
            except ValueError:
                # option doesn't exist in structure
                structure.insert(-1 if pos is None else pos, option)

    @copy_doc(_set_option, annotations=True)
    def set_option(self, *args, **kwargs) -> ...:
        return self._set_option(*args, **kwargs)

    def _get_options(self) -> dict[str, Option]:
        """Get all options of the section.

        Returns:
            dict[str, Option]: Variable names as keys and Options as values.
        """
        return {
            name: var for name, var in vars(self).items() if isinstance(var, Option)
        }

    @copy_doc(_get_options, annotations=True)
    def get_options(self, *args, **kwargs) -> ...:
        return self._get_options(*args, **kwargs)

    def _get_comment_by_content(self, content: str | re.Pattern) -> dict[str, Comment]:
        """Get a comment by its content.

        Args:
            content (str | re.Pattern): The content of the comment.

        Returns:
            dict[str, Comment]: All comments that fit the content argument with variable
                names as keys and the Comment objects as values.
        """
        content = (
            content.pattern if isinstance(content, re.Pattern) else re.escape(content)
        )
        return {
            name: var
            for name, var in vars(self).items()
            if isinstance(var, Comment) and re.search(var.content, content)
        }

    @copy_doc(_get_comment_by_content, annotations=True)
    def get_comment_by_content(self, *args, **kwargs) -> ...:
        return self._get_comment_by_content(*args, **kwargs)

    def _get_comments(self) -> dict[str, Comment]:
        """Get all comments of the section.

        Returns:
            dict[str, Comment]: Variable names as keys and Comments as values.
        """
        return {
            name: var for name, var in vars(self).items() if isinstance(var, Comment)
        }

    @copy_doc(_get_comments, annotations=True)
    def get_comments(self, *args, **kwargs) -> ...:
        return self._get_comments(*args, **kwargs)

    def _get_next_comment_var(self) -> str:
        """Get the variable name for the next comment.

        Returns:
            str: The variable name of the next comment.
        """
        comment_ids = tuple(
            int(cid[0])
            for name, _ in self._get_comments().items()
            if (cid := re.search(rf"(?<=^{COMMENT_VAR_PREFIX})\d+$", name))
        )
        return COMMENT_VAR_PREFIX + str(comment_ids[-1] + 1 if comment_ids else 0)


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
        if __bases and StructureSlotEntity not in __bases and Schema in __bases:
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


class Schema(StructureSlotEntity[Section], metaclass=_SchemaMeta):

    def __init__(
        self,
        parameters: Parameters | None = None,
        method: SlotDeciderMethods = "default",
        **kwargs,
    ) -> None:
        """Schema class. Parameters will be stored as default read and write parameters.

        Args:
            parameters (Parameters | None, optional): Default parameters for reading and
                writing inis, as an Parameters object. Parameters can also be passed
                as kwargs. Missing parameters (because parameters is None and no or not
                enough kwargs are passed) will be taken from default Parameters
                (see doc of Parameters). Defaults to None.
            method ("default" | "first" | "latest", optional): Method for choosing
                the slot. "default" will use slot 0 whenenver latest slot is None,
                "first" will use first slot, "latest" the last slot that was added.
                Defaults to "default".
            **kwargs (optional): Parameters as kwargs. See Parameters doc for details.
        """
        super().__init__()
        ### read arguments ###
        if parameters is None:
            parameters = Parameters()
        if kwargs:
            parameters.update(**kwargs)
        self._default_parameters = parameters
        self._decider_method = method
        self.iloc = SlotIlocViewer(self)

    def __getattribute__(self, name: str) -> Any:
        attr = super().__getattribute__(name)
        if isinstance(attr, Section):
            return SlotDecider(
                target=attr, slots=self._slots, decider_method=self._decider_method
            )
        return attr

    def __getitem__(self, key: SlotAccess) -> Self:
        return SlotViewer(target=self, slot=key)

    def __setitem__(self, *_, **__) -> None:
        raise TypeError("Schema doesn't support item assignment.")

    def _with_slot(self, slot: SlotAccess) -> Self:
        """Access the ini using a specific slot.

        Args:
            slot (SlotAccess): The slot to use.
        """
        return self[slot]

    @copy_doc(_with_slot, annotations=True)
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

    @copy_doc(_get_sections, annotations=True)
    def get_sections(self, *args, **kwargs) -> ...:
        return self._get_sections(*args, **kwargs)

    def _read_ini(
        self,
        path: str | Path,
        parameters: Parameters | None = None,
        parameters_as_default: bool = False,
        *,
        slots: SlotAccess | Literal[False] = False,
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
            slots (SlotAccess | False, optional): Slot(s) to save the content in.
                If False will create new slot. Defaults to False.
        """
        # define parameters
        if parameters is None:
            # take parameters from copy of self._parameters
            parameters = self._default_parameters
        assert isinstance(parameters, Parameters)
        if kwargs:
            parameters.update(**kwargs)
        if parameters_as_default:
            self._default_parameters = parameters
        if slots is False:
            # Generate new slot key
            slot_keys = self._slots.keys()
            len_slots = len(slot_keys)
            slots = next(
                slot_key
                for slot_key in range(
                    len_slots,
                    len_slots * 2 + 1,
                )
                if slot_key not in slot_keys
            )
            self._slots.add(slots)
        else:
            slots = self._slots.slot_access(slots, verify=True)

        with open(path, "r") as file:
            file_content = file.read()

        current_option: Option | None = None
        # get unnamed section, delete later if undefined and unused
        current_section = self._get_unnamed_section(parameters=parameters)
        current_section_structure: list[Option | Comment] = []

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
                    if current_section and current_section_structure:
                        # reorder old section structure and reset for new section
                        current_section._set_structure(
                            new_structure=current_section_structure,
                            slots=slots,
                            create_missing_slots=True,
                        )
                        current_section_structure = []
                    current_section = self._handle_section_name(
                        extracted_section_name, parameters, slots=slots
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
                if option := self._extract_option(
                    entity_content, parameters, slots=slots
                ):
                    if handled_option := self._handle_option(
                        option, parameters, current_section, slots=slots
                    ):
                        current_option = handled_option
                        current_section_structure.append(current_option)
                        continue

            # try to extract comment
            if (
                not possible_continuation
                or "comment" not in parameters.continuation_ignore
            ):
                if comment := self._extract_comment(entity_content, parameters):
                    comment = self._handle_comment(
                        comment, current_section, slots=slots
                    )
                    current_section_structure.append(comment)
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
            self._handle_continuation(entity_content, current_option, slots=slots)

        if (
            isinstance(
                unnamed := self._get_unnamed_section(parameters), UndefinedSection
            )
            and unnamed.nslot == 0
        ):
            del unnamed

    @copy_doc(_read_ini, annotations=True)
    def read_ini(self, *args, **kwargs) -> ...:
        return self._read_ini(*args, **kwargs)

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
        *,
        slots: SlotAccess,
    ) -> Section | None:
        """Handle an extracted SectionName (add new section if necessary).

        Args:
            section_name (SectionName): The extracted section name.
            parameters (Parameters): Ini read and write parameters.
            slots (SlotAccess): Slots that the section should have.

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
            if parameters.read_undefined not in (True, "section"):
                # section is not defined and undefined sections are not allowed, thus
                return None

            # undefined section
            section_var = _str_to_var(extracted_section_name)
            section = UndefinedSection(extracted_section_name)
            setattr(self, section_var, section)

        # make sure section is in slots
        self._insert_structure_items(section, -1, exist_ok=True, slots=slots)
        # add slot to section
        section._add_slots(keys=slots, exist_ok=True)

        return section

    def _extract_option(
        self, entity: str, parameters: Parameters, *, slots: SlotAccess
    ) -> Option | None:
        """Extract an option if present in entity.

        Args:
            entity (str): The entity to extract the section from.
            parameters (Parameters): Ini read and write parameters.
            slots (SlotAccess): Slot(s) the new option should have.

        Returns:
            Option | None: The extracted option or None if no option was found in entity.
        """
        try:
            return Option.from_string(
                string=entity, delimiter=parameters.option_delimiters, slots=slots
            )
        except ExtractionError:
            return None

    def _handle_option(
        self,
        extracted_option: Option,
        parameters: Parameters,
        section: Section,
        *,
        slots: SlotAccess,
    ) -> Option | None:
        """Handle an extracted Option.

        Args:
            extracted_option (Option): Extracted option to handle.
            parameters (Parameters): Ini read and write parameters.
            section (Section): The section to add the option to.
            slot (SlotAccess): Slot(s) to save option values in and add to the section.

        Returns:
            Option | None: The final Option in the section (differs from input) or None
                if Option could not be handled (e.g. due to undefined and undefined not
                allowed in parameters).
        """
        # check if Option is defined
        try:
            option = section._get_option(key=extracted_option.key)
            # add slot if needed

            option._set_slots(
                new_slot_value=extracted_option.iloc[-1][1],
                slots=slots,
                create_missing_slots=True,
            )
        except EntityNotFound:
            if parameters.read_undefined in {True, "option"}:
                # create UndefinedOption
                option = section._add_entity(extracted_option, slots=slots)
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
        self, extracted_comment: Comment, section: Section, *, slots: SlotAccess
    ) -> Comment:
        """Handle an extracted Comment (add it to section if necessary).

        Args:
            extracted_comment (Comment): Extracted comment to handle.
            section (Section): The section to add the comment to.
            slot (SlotAccess): Slot to add the comment to in the section.

        Returns:
            Comment: The comment added to the section
                (as of now the input Comment object).

        """
        section._add_entity(extracted_comment, positions=-1, slots=slots)
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

    def _handle_continuation(
        self, continuation: str, last_option: Option, *, slots: SlotAccess
    ) -> None:
        """Handles a continutation (adds it to the last option).

        Args:
            continuation (str): The continuation.
            last_option (Option): The last option to add the continuation to.
            slot (SlotAccess): Slot to add the continuation to.
        """
        # add continuation to last option
        last_option._apply_to_slots(
            lambda val: (
                [*val, continuation] if isinstance(val, list) else [val, continuation]
            ),
            slots=slots,
        )

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

    def __init__(self, target: Schema | Section) -> None:
        super().__setattr__("_target", target)
        super().__setattr__("_slot_views", {})

    def _slot_access(self, access_target: Callable, slot: SlotAccess) -> Callable:
        """Access a callable and set the slot accordingly.

        Args:
            access_target (Callable): The callable to access.
            slot (SlotAccess): The slot(s) to access.

        Returns:
            Callable: A function that mimics the requested Callable but sets the
                SlotAccess argument to self._slot.
        """
        access_kwarg = next(
            k
            for k, v in inspect.get_annotations(access_target).items()
            if v == SlotAccess
        )
        assert isinstance(access_kwarg, str)

        def accesser_func(*args, **kwargs):
            kwargs[access_kwarg] = slot
            return access_target(*args, **kwargs)

        return accesser_func

    def _set_slot(self, name: str, value: Any, slot: SlotAccess) -> None:
        target, attr = super().__getattribute__("_get_target_attr")(name)
        if not (isinstance(attr, Option) and isinstance(target, Section)):
            raise AttributeError("Assignment only valid for options.")
        super().__getattribute__("_slot_access")(
            access_target=target._set_option, slot=slot
        )(name=name, value=value)

    def _get_target_attr(self, name: str) -> tuple[Schema | Section, Any]:
        target = super().__getattribute__("_target")
        attr = target.__dict__.get(name, None) or getattr(target, name)
        return (target, attr)


class SlotDecider(SlotView):

    def __init__(
        self, target: Section, slots: Slots, decider_method: SlotDeciderMethods
    ) -> None:
        """Gives access to slots by deciding.

        Args:
            target (Section): The target to prepare for slot access.
            slots (Slots): The slots to take as reference.
            decider_method (SlotDeciderMethods): The method to use for decision.
        """
        super().__init__(target=target)
        super().__setattr__("_decider_method", decider_method)
        super().__setattr__("_slots", slots)

    def __getattribute__(self, name: str) -> Any:
        if name in {
            "__getattribute__",
            "__setattr__",
            "__init__",
            "__new__",
            "__call__",
        }:
            return super().__getattribute__(name)
        target, attr = super().__getattribute__("_get_target_attr")(name)

        if isinstance(attr, Option):
            return super().__getattribute__("_decide_slot")(attr)[1]
        elif (
            not name.startswith("__")
            and callable(attr)
            and SlotAccess in inspect.get_annotations(attr).values()
        ):
            slot_key = super().__getattribute__("_decide_slot")(target)[0]
            return super().__getattribute__("_slot_access")(attr, slot_key)

        return attr

    def __setattr__(self, name: str, value: Any) -> None:
        _, attr = super().__getattribute__("_get_target_attr")(name)
        slot = super().__getattribute__("_decide_slot")(attr)[0]
        super().__getattribute__("_set_slot")(name, value, slot)

    def _decide_slot(self, target: Option | Section) -> tuple[
        SlotKey,
        OptionSlot | Structure,
    ]:
        """Decides, which slot to access using the defined decider method.

        Args:
            target (Option | Section): The Option or Section that is to be accessed.

        Returns:
            tuple[SlotKey, OptionSlot | SectionStructure]: Tuple of the target's
                decided slot's key and value.

        """
        decider_method: SlotDeciderMethods = super().__getattribute__("_decider_method")
        slots: Slots = super().__getattribute__("_slots")

        latest_key = slots.iloc[-1][0]
        first_key = slots.iloc[0][0]

        match decider_method:
            case "default":
                latest_val = target._get_slots(latest_key)
                return (
                    (latest_key, latest_val)
                    if latest_val is not None
                    else (first_key, target._get_slots(first_key))
                )
            case "first":
                return first_key, target._get_slots(first_key)
            case "latest":
                return latest_key, target._get_slots(latest_key)


class SlotViewer(SlotView):

    def __init__(
        self,
        target: Schema | Section,
        slot: SlotAccess,
    ) -> None:
        """Gives access to a specific slot.

        Args:
            target (Schema | Section): The target to prepare for slot access.
            slot (SlotAccess): The slot to access.
        """
        super().__init__(target=target)
        super().__setattr__("_slot", slot)

    def __getattribute__(self, name: str) -> Any:

        if name in {
            "__getattribute__",
            "__setattr__",
            "__init__",
            "__new__",
            "__call__",
            "__class__",
        }:
            return super().__getattribute__(name)

        target, attr = super().__getattribute__("_get_target_attr")(name)
        slot: SlotAccess = super().__getattribute__("_slot")

        # Schema[].Section
        if isinstance(attr, Section):
            assert isinstance(target, Schema)
            return SlotViewer(target=attr, slot=slot)

        # Schema[].Section.Option
        elif isinstance(attr, Option):
            assert isinstance(target, Section)
            return attr[slot]

        # Schema[].Section.(SlotAccess)
        elif callable(attr):
            return super().__getattribute__("_slot_access")(attr, slot)

        return attr

    def __setattr__(self, name: str, value: Any) -> None:
        slot: SlotAccess = super().__getattribute__("_slot")
        super().__getattribute__("_set_slot")(name, value, slot)

    def _export(self, path: str | Path) -> None:
        path = Path(path)
        # TODO


class SlotIlocViewer(SlotView):

    def __init__(
        self,
        target: Schema,
    ) -> None:
        """Gives access to a specific slot by index.

        Args:
            target (Schema): The target to prepare for slot access.
        """
        super().__init__(target)

    def __getitem__(self, index: int) -> SlotViewer:
        if not isinstance(index, int):
            raise ValueError("Indexing only works with int.")
        target: Schema = super().__getattribute__("_target")
        try:
            requested_slot = target._slots.iloc[index][0]
        except IndexError as e:
            raise IndexError("Slots index out of range.") from e
        return SlotViewer(target=target, slot=requested_slot)
