"""Interface classes exist for coder interaction, to simplify the process
behind smartini."""

from typing import (
    Any,
    Literal,
    Self,
    Callable,
    overload,
    get_type_hints,
)
import re
from pathlib import Path
import warnings
import contextlib
from charset_normalizer import from_bytes as read_from_bytes
from .exceptions_warnings import (
    MultilineWarning,
    IniStructureWarning,
    ExtractionError,
    EntityNotFound,
    DuplicateEntityError,
    UndefinedOptionWarning,
    UndefinedSectionWarning,
)
from .entities import (
    Comment,
    CommentGroup,
    Option,
    OptionValue,
    OptionSlotValue,
    SectionName,
    UndefinedOption,
)
from .slots import (
    SlotAccess,
    SlotKey,
    SlotDeciderMethods,
    Slots,
    _StructureSlotEntity,
    Structure,
)
from .args import Parameters
from .globals import (
    COMMENT_VAR_PREFIX,
    UNNAMED_SECTION_NAME,
    SECTION_NAME_VARIABLE,
    INTERNAL_PREFIX,
    INTERNAL_PREFIX_IN_WORDS,
)
from .utils import _str_to_var, OrderedDict, copy_doc
from .type_converters.type_hints import _resolve_TYPE


class SectionMeta(type):
    """Metaclass for ini configuration file sections."""

    # name of the section if actual section name differs from class variable
    _name: str | None

    def __new__(cls, __name: str, __bases: tuple, __dict: dict):
        #  make sure it's the initialization call
        if (
            __bases
            and _StructureSlotEntity not in __bases
            and Section in __bases
            and __name != "UndefinedSection"
            and SECTION_NAME_VARIABLE not in __dict
        ):
            __dict[SECTION_NAME_VARIABLE] = __name
        return super().__new__(cls, __name, __bases, __dict)


class Section(_StructureSlotEntity[Option | Comment], metaclass=SectionMeta):
    """A configuration section. Holds Options and Comments. If the actual section name
    differs from class variable, it needs to be assigned to the "_name" class attribute!
    Furthermore, class attributes holding options must not start with
    a leading underscore!
    """

    # name of the section if actual section name differs from class variable
    _name: str | None

    def __init__(self) -> None:

        super().__init__()

        type_hints = get_type_hints(self)

        # initialize Options
        for var, val in vars(self.__class__).items():
            # every string variable without leading and trailing underscores
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

                # create option and add to Section
                option = Option(
                    key=val,
                    type_converter=(
                        _resolve_TYPE(type_hints[var]) if var in type_hints else None
                    ),
                )
                super().__setattr__(var, option)
                self._schema_structure.append(option)

    @overload
    def _add_entity(
        self,
        entity: UndefinedOption | Option,
        positions: int | list[int | None] | None = None,
        *,
        slots: SlotAccess = None,
    ) -> UndefinedOption: ...
    @overload
    def _add_entity(
        self,
        entity: Comment,
        positions: int | list[int | None] | None = None,
        *,
        slots: SlotAccess = None,
    ) -> Comment: ...

    def _add_entity(
        self,
        entity: UndefinedOption | Option | Comment,
        positions: int | list[int | None] | None = None,
        *,
        slots: SlotAccess = None,
    ) -> UndefinedOption | Comment:
        """Add a new entity to the section.

        Args:
            entity (UndefinedOption | Option | Comment): The entity to add.
            positions (int | list[int | None] | None): Position in slots the entity
                should take. Either int for same position in all slots or one position
                per slot. If None and for every slot that None is specified for,
                will append to slots. Defaults to None.
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
        self._set_structure_items(items=entity, positions=positions, slots=slots)

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
            key (SlotKey | None, optional): The option key. Will be ignored if name is
                not None. Defaults to None.

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

    @overload
    def _get_options(
        self,
        include_undefined: Literal[False] = ...,
        *,
        slots: SlotAccess = None,
    ) -> OrderedDict[str, Option]: ...
    @overload
    def _get_options(
        self,
        include_undefined: Literal[True] = True,
        *,
        slots: SlotAccess = None,
    ) -> OrderedDict[str, Option | UndefinedOption]: ...
    @overload
    def _get_options(
        self,
        include_undefined: Literal["only"] = ...,
        *,
        slots: SlotAccess = None,
    ) -> OrderedDict[str, UndefinedOption]: ...

    def _get_options(
        self,
        include_undefined: bool | Literal["only"] = True,
        *,
        slots: SlotAccess = None,
    ) -> (
        OrderedDict[str, Option | UndefinedOption]
        | OrderedDict[str, Option]
        | OrderedDict[str, UndefinedOption]
    ):
        """Get the Section's options.

        Args:
            include_undefined (bool | "only", optional): Whether to include undefined
                options. If "only", will return only undefined options. Always False
                if slots is not None.
            slots (SlotAccess, optional): Which slot(s) to get options from. If multiple
                are given, will return the intersection. If None will return all.
                Defaults to None.

        Returns:
            OrderedDict[str, Option | UndefinedOption] | OrderedDict[str, Option]
                | OrderedDict[str, UndefinedOption]: Variable names as keys and options as
                values. Order is that of the slot structure if len(slots) == 1.
                Otherwise, order matches original schema structure with undefined options
                at the end.
        """
        return self._get_items(  # type: ignore
            defined_item=Option,
            undefined_item=UndefinedOption,
            include_undefined=include_undefined,  # type: ignore
            slots=slots,
        )

    @copy_doc(_get_options, annotations=True)
    def get_options(self, *args, **kwargs) -> ...:
        return self._get_options(*args, **kwargs)

    @classmethod
    def _get_option_variable_names(cls) -> OrderedDict[str, Option]:
        """Get variable names of all options this section owns.

        Returns:
            OrderedDict[str, Option]: Variable names as keys, Options as values.
        """
        out = OrderedDict()
        for var, val in vars(cls).items():
            # every string variable without leading and trailing underscores
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
                out[var] = Option(key=val)
        return out

    @overload
    def _set_option(
        self,
        name: str,
        value: OptionValue,
        positions: int | list[int | None] | None = None,
        key: ... = ...,
        *,
        slots: SlotAccess = None,
    ) -> None: ...
    @overload
    def _set_option(
        self,
        name: None,
        value: OptionValue,
        positions: int | list[int | None] | None = None,
        key: str = ...,
        *,
        slots: SlotAccess = None,
    ) -> None: ...

    def _set_option(
        self,
        name: str | None,
        value: OptionValue,
        positions: int | list[int | None] | None = None,
        key: str | None = None,
        *,
        slots: SlotAccess = None,
    ) -> None:
        """Set an option's value by accessing it via variable name or option key.

        Args:
            name (str | None): The variable name of the option. Must be None if key
                should be used.
            value (OptionValue): The new value for the option.
            positions (int | list[int | None] | None): Position in slots the entity
                should take. Either int for same position in all slots or one position
                per slot. If None and for every slot that None is specified for,
                will take previous position of the Option in the respective slot and
                will append to slots where Option didn't exist before.
                Defaults to None.
            key (str | None, optional): The option key. Will be ignored if name
                is not None. Defaults to None.
            slots (SlotAccess, optional): The slot to use. Defaults to None (all slots).
        """
        if key is None:
            if name is None:
                raise ValueError("Need name or key for option setting.")
        elif name is not None:
            warnings.warn("Key passed but name is not None. Taking name.")

        # get option
        try:
            option: Option = self._get_option(name, key)
        except EntityNotFound:
            try:
                option = UndefinedOption(values=value, slots=slots)
                self._add_entity(option, slots=slots, positions=positions)
                return
            except ExtractionError as ee:
                raise ValueError(
                    "Can't add new option because of insufficient initialization arguments."
                ) from ee

        # set option value
        option._set_slots(value=value, slots=slots, create_missing_slots=True)

        # set structure position
        self._set_structure_items(
            items=option, positions=positions, exist_action="move_not_None", slots=slots
        )

    @copy_doc(_set_option, annotations=True)
    def set_option(self, *args, **kwargs) -> ...:
        return self._set_option(*args, **kwargs)

    def _get_comments_by_content(self, content: str | re.Pattern) -> dict[str, Comment]:
        """Get comments matching the content.

        Args:
            content (str | re.Pattern): The content to search for.

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
            if isinstance(var, Comment) and re.search(content, var.content)
        }

    @copy_doc(_get_comments_by_content, annotations=True)
    def get_comments_by_content(self, *args, **kwargs) -> ...:
        return self._get_comments_by_content(*args, **kwargs)

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

    def _assign_comments_to_options(
        self, *, slots: SlotAccess = None
    ) -> OrderedDict[Option, OrderedDict[SlotKey, CommentGroup]]:
        """Assigns each comment to its following Option. Comments at the end of the section
        (with no following option) will be assigned to "None".

        Args:
            slots (SlotAccess, optional): The slot(s) to use. If multiple are given, will
                assign the comments per slot.

        Returns:
            OrderedDict[Option,CommentGroup] |
            OrderedDict[Option,dict[SlotKey,CommentGroup]]: Options as keys.
                Value is a dictionary with SlotKeys as keys and the Comments as values.
        """
        slots = self._slots.slot_access(slots)

        out = OrderedDict()

        for slot in slots:

            # temp save comments here
            comments = CommentGroup()

            for entity in self._slots[slot]:
                if isinstance(entity, Comment):
                    comments.append(entity)
                elif isinstance(entity, Option):
                    out[entity] = out.get(entity, OrderedDict()) | {slot: comments}
                    comments = CommentGroup()
            if comments:
                out[None] = out.get(None, OrderedDict()) | {slot: comments}

        return out


class UndefinedSection(Section):
    """Class for sections that are not user-defined in the provided schema."""

    def __init__(self, section_name: str | None) -> None:
        """
        Args:
            section_name (str | None): Name of the section.
        """
        setattr(self, SECTION_NAME_VARIABLE, section_name)
        super().__init__()


class _SchemaMeta(type):
    """Metaclass for schema class."""

    def __new__(cls, __name: str, __bases: tuple, __dict: dict):
        #  make sure it's the initialization call
        if __bases and _StructureSlotEntity not in __bases and Schema in __bases:
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


class Schema(_StructureSlotEntity[Section], metaclass=_SchemaMeta):
    """Schema class to define configuration schema and access loaded configurations."""

    def __init__(
        self,
        parameters: Parameters | None = None,
        method: SlotDeciderMethods = "fallback",
        **kwargs,
    ) -> None:
        """Parameters will be stored as default read and write parameters.

        Args:
            parameters (Parameters | None, optional): Default parameters for reading and
                writing INIs, as a Parameters object. Parameters can also be passed
                as kwargs. Missing parameters (because parameters is None and no or not
                enough kwargs are passed) will be taken from default parameters
                (see doc of Parameters). Defaults to None.
            method (SlotDeciderMethods, optional): Method for choosing the slot.
                Defaults to "fallback".
            **kwargs (optional): Parameters as kwargs. See Parameters doc for details.
        """
        super().__init__()
        ### read arguments ###
        if parameters is None:
            parameters = Parameters()
        if kwargs:
            parameters.update(**kwargs)
        self._default_parameters = parameters
        self._decider_method: SlotDeciderMethods = method
        self._slot_decider = SlotDecider(self, self._slots, method)
        self.iloc = SlotIlocViewer(self)

        # initialize Sections
        for var, val in vars(self.__class__).items():
            if isinstance(val, SectionMeta):
                section = val()
                super().__setattr__(var, section)
                self._schema_structure.append(section)

    def __getattribute__(self, name: str) -> Any:
        attr = super().__getattribute__(name)
        if isinstance(attr, Section):
            return SlotDecider(
                target=attr, slots=self._slots, decider_method=self._decider_method
            )
        return attr

    def __getitem__(self, key: SlotAccess) -> Any:
        return SlotViewer(target=self, slot=key)

    def _with_slot(self, slot: SlotAccess) -> Self:
        """Access the ini using a specific slot. Equivalent to item access via brackets
        (i.e. Schema[slot]).

        Args:
            slot (SlotAccess): The slot to use.
        """
        return self[slot]

    @copy_doc(_with_slot, annotations=True)
    def with_slot(self, *args, **kwargs) -> ...:
        return self._with_slot(*args, **kwargs)

    def _get_section(
        self, section_name: SectionName | str | None
    ) -> tuple[str, Section]:
        """Get a section by its name.

        Args:
            section_name (SectionName | str | None): The name of the section to get.

        Raises:
            EntityNotFound: If the section was not found by its name.

        Returns:
            tuple[str, Section]: Tuple of variable name and section object.
        """
        try:
            return next(
                (var, val)
                for var, val in vars(self).items()
                if isinstance(val, Section)
                and getattr(val, SECTION_NAME_VARIABLE) == section_name
            )
        except StopIteration as e:
            raise EntityNotFound(
                f"Can't get section '{section_name}' because it doesn't exist."
            ) from e

    @copy_doc(_get_section, annotations=True)
    def get_section(self, *args, **kwargs) -> ...:
        return self._get_section(*args, **kwargs)

    @overload
    def _get_sections(
        self,
        include_undefined: Literal[False] = ...,
        *,
        slots: SlotAccess = None,
    ) -> OrderedDict[str, Section]: ...
    @overload
    def _get_sections(
        self,
        include_undefined: Literal[True] = True,
        *,
        slots: SlotAccess = None,
    ) -> OrderedDict[str, Section | UndefinedSection]: ...
    @overload
    def _get_sections(
        self,
        include_undefined: Literal["only"] = ...,
        *,
        slots: SlotAccess = None,
    ) -> OrderedDict[str, UndefinedSection]: ...

    def _get_sections(
        self,
        include_undefined: bool | Literal["only"] = True,
        *,
        slots: SlotAccess = None,
    ) -> (
        OrderedDict[str, Section | UndefinedSection]
        | OrderedDict[str, Section]
        | OrderedDict[str, UndefinedSection]
    ):
        """Get the Schemas's sections.

        Args:
            include_undefined (bool | "only", optional): Whether to include undefined
                sections. If "only", will return only undefined sections. Always False
                if slots is not None.
            slots (SlotAccess, optional): Which slot(s) to get sections from. If multiple
                are given, will return the intersection. If None will return all.
                Defaults to None.

        Returns:
            OrderedDict[str, Section | UndefinedSection] | OrderedDict[str, Section]
                | OrderedDict[str, UndefinedSection]: Variable names as keys and sections
                as values. Order is that of the slot structure if len(slots) == 1.
                Otherwise, order matches original schema structure with undefined sections
                at the end.
        """
        return self._get_items(  # type: ignore
            defined_item=Section,
            undefined_item=UndefinedSection,
            include_undefined=include_undefined,  # type: ignore
            slots=slots,
        )

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
        """Read an INI file. If no parameters are passed (as Parameters object or kwargs),
        default parameters defined on initialization will be used.

        Args:
            path (str | Path): Path to the INI file.
            parameters (Parameters | None, optional): Parameters for reading and
                writing INIs, as a Parameters object. Parameters can also be passed
                as kwargs. Missing parameters (because parameters is None and no or not
                enough kwargs are passed) will be taken from default parameters that
                were defined on initialization. Defaults to None.
            parameters_as_default (bool, optional): Whether to save the parameters for
                this read as default parameters. Defaults to False.
            slots (SlotAccess | False, optional): Slot(s) to save the content in.
                If False will create new slot. Defaults to False.
            **kwargs (optional): Parameters as kwargs. See doc of Parameters for details.
        """
        _ReadIni(
            target=self,
            path=path,
            parameters=parameters,
            parameters_as_default=parameters_as_default,
            slots=slots,
            **kwargs,
        )

    @copy_doc(_read_ini, annotations=True)
    def read_ini(self, *args, **kwargs) -> ...:
        return self._read_ini(*args, **kwargs)

    def _export(
        self,
        path: str | Path,
        structure: Literal["schema", "content"] | None = None,
        decider_method: SlotDeciderMethods | None = None,
        include_undefined: bool = True,
        export_comments: bool = False,
        *,
        content_slots: SlotAccess = None,
    ) -> None:
        """Export the saved configuration to a file.

        Args:
            path (str | Path): Path to the file to export to.
            structure ("schema" | "content" | None, optional): Slot to use for
                structuring the output (including comments). If "schema", will use
                original schema definition. If "content", will use slot that is used
                as content slot (if multiple content slots are given will use the first).
                If None will use "schema" if content_slots is None and "content"
                otherwise. Defaults to None.
            decider_method (SlotDeciderMethods | None, optional): Either a decider method
                to use or None to use the initial decider method. Defaults to None.
            include_undefined (bool, optional): Whether to include undefined entities.
                Defaults to True.
            export_comments (bool, optional): Whether to export comments. Will use first
                content slot to get comments from. Comments will be matched to following
                entities (e.g. all comments above option_a will be above option_a in the
                exported ini). Defaults to False.
            content_slots (SlotAccess, optional): Slot(s) to use for content (sections
                and options). If multiple are given, first slot has priority, then
                second (if first is None) and so on. If None, will use decider method.
                Defaults to None.
        """
        # get slot access for content
        access = self._slots.slot_access(content_slots, verify=True)
        if content_slots is None:
            match (decider_method or self._decider_method):
                case "fallback":
                    access = [access[-1]] + ([access[0]] if len(access) > 1 else [])
                case "first":
                    access = [access[0]]
                case "latest":
                    access = [access[-1]]
                case "cascade down":
                    access = list(reversed(access))

        # define structure to use
        _schema_structure = lambda section: section._schema_structure
        _content_structure = lambda section: section[access[0]]

        match structure:
            case "schema":
                entities_structure = _schema_structure
            case "content":
                entities_structure = _content_structure
            case _:
                entities_structure = (
                    _schema_structure if content_slots is None else _content_structure
                )
                structure = "schema"

        # get markers
        option_delimiter = self._default_parameters.option_delimiters[0]
        comment_prefix = (
            self._default_parameters.comment_prefixes[0]
            if self._default_parameters.comment_prefixes
            else None
        )

        # define last variables
        if include_undefined:
            valid_option = lambda entity: isinstance(entity, Option)
        else:
            valid_option = lambda entity: isinstance(entity, Option) and not isinstance(
                entity, UndefinedOption
            )
        big_space: str = "\n" * 2

        out = ""

        for sec in self._get_sections(  # type: ignore
            include_undefined=include_undefined,  # type: ignore
            slots=None if structure == "schema" else access,
        ).values():
            comments = None

            if export_comments:
                comments = sec._assign_comments_to_options(slots=access[0])

            # add section name
            if (section_name := getattr(sec, SECTION_NAME_VARIABLE)) is not None:
                out += f"[{section_name}]{big_space}"

            for entity in entities_structure(sec):
                if valid_option(entity):
                    # add comments if requested
                    if comments is not None and entity in comments:
                        out += comments[entity].iloc[0][1].to_string(comment_prefix)
                        out += "\n"

                    # add option
                    out += entity.to_string(option_delimiter, slots=access)
                    out += big_space

            if comments is not None and None in comments:
                # add comments from end of the section
                out += comments[None].iloc[0][1].to_string(comment_prefix)
                out += big_space

        # remove last extra delimiters
        out = out[: -len(big_space)]

        Path(path).write_text(out, encoding="utf-8")

    @copy_doc(_export, annotations=True)
    def export(self, *args, **kwargs) -> ...:
        return self._export(*args, **kwargs)


class _ReadIni:

    def __init__(
        self,
        target: Schema,
        path: str | Path,
        parameters: Parameters | None = None,
        parameters_as_default: bool = False,
        *,
        slots: SlotAccess | Literal[False] = False,
        **kwargs,
    ) -> None:
        """Read an ini file into target. For more info cf. Schema._read_ini."""
        self.target = target

        # define parameters
        if parameters is None:
            # take parameters from copy of self._parameters
            self.parameters = target._default_parameters
        else:
            self.parameters = parameters
        assert isinstance(self.parameters, Parameters)
        if kwargs:
            self.parameters.update(**kwargs)
        if parameters_as_default:
            self.target._default_parameters = self.parameters

        if slots is False:
            # Generate new slot key
            slot_keys = self.target._slots.keys()
            len_slots = len(slot_keys)
            self.slots = next(
                slot_key
                for slot_key in range(
                    len_slots,
                    len_slots * 2 + 1,
                )
                if slot_key not in slot_keys
            )
            self.target._slots.add(slots)
        else:
            self.slots = self.target._slots.slot_access(slots, verify=True)

        # read file
        file_content = str(read_from_bytes(Path(path).read_bytes()).best())

        # split into entities
        entities = file_content.split("\n")

        # ----
        # define variables for read process
        # ----
        self.current_option: Option | None | Literal[False] = None
        """If None then no Option in the line before. If False, then ignored
        UndefinedOption in the line before."""

        # get unnamed section, delete later if undefined and unused
        self.current_section = self._get_unnamed_section()
        self.current_section_structure: list[Option | Comment] = []

        self.current_entity_index: int = 0
        self.current_entity_content: str = ""

        self.possible_continuation: bool = False
        # ----

        for self.current_entity_index, self.current_entity_content in enumerate(
            entities
        ):

            self.current_entity_content, self.possible_continuation = (
                self._check_for_possible_continuation()
            )

            if self._is_empty_entity():
                # empty entity, skip and close off last option
                self.current_option = None

            # try to extract section
            elif extracted_section_name := self._extract_section_name():
                if self.current_section and self.current_section_structure:
                    # reorder old section structure and reset for new section
                    self.current_section._set_structure(
                        new_structure=self.current_section_structure,
                        slots=self.slots,
                        create_missing_slots=True,
                    )
                    self.current_section_structure = []
                self.current_section = self._handle_section_name(extracted_section_name)
                self.current_option = None

            elif not self.current_section:
                # we need a current section to extract options and comments
                if self.current_section is False:
                    warnings.warn(
                        f"Line {self.current_entity_index} is being ignored because it's inside an undefined section and read_undefined is set to {self.parameters.read_undefined}.",
                        UndefinedSectionWarning,
                    )

            # try to extract comment
            elif comment := self._extract_comment():
                comment = self._handle_comment(comment)
                self.current_section_structure.append(comment)

            # try to extract option
            elif option := self._extract_option():
                self.current_option = self._handle_option(option)
                if self.current_option:
                    self.current_section_structure.append(self.current_option)

            else:
                # handle continuation
                self._handle_continuation()

        if (
            isinstance(
                unnamed := self._get_unnamed_section(),
                UndefinedSection,
            )
            and unnamed.nslot == 0
        ):
            delattr(target, UNNAMED_SECTION_NAME)

    def _get_unnamed_section(self) -> Section | None:
        """Get the unnamed section (always at the beginning of the ini).

        Returns:
            Section | None: The unnamed section or None if unnamed section undefined
                and not allowed.
        """
        # check if unnamed section is in schema else create UndefinedSection
        try:
            varname, section = self.target._get_section(None)
        except EntityNotFound:
            if self.parameters.read_undefined in {True, "section"}:
                section = UndefinedSection(section_name=None)
                varname = UNNAMED_SECTION_NAME
                setattr(self.target, varname, section)
            else:
                section = None

        return section

    def _extract_section_name(self) -> SectionName | None:
        """Extract a section name if present in self.current_entity_content.

        Returns:
            SectionName | None: The extracted section name or None if no section name
                was found in self.current_entity_content.
        """
        if (
            not self.possible_continuation
            or "section_name" not in self.parameters.multiline_ignore
        ):
            with contextlib.suppress(ExtractionError):
                return SectionName(name_with_brackets=self.current_entity_content)
        return None

    def _handle_section_name(
        self,
        extracted_section_name: SectionName,
    ) -> Section | None | Literal[False]:
        """Handle an extracted SectionName (add new section if necessary).

        Returns:
            Section | None: The section belonging to the extracted SectionName or None
                if no section belongs to it (i.e. no section could be created because
                of Parameters) or False if section is undefined but undefined sections
                are being ignored.
        """

        # check if Section exists in schema
        try:
            section_var, section = self.target._get_section(extracted_section_name)
        except EntityNotFound:
            if self.parameters.read_undefined not in {True, "section"}:
                # section is not defined and undefined sections are not allowed, thus
                warnings.warn(
                    f"Line {self.current_entity_index} is not a defined section, thus the whole section is being ignored (read_undefined is set to {self.parameters.read_undefined}).",
                    UndefinedSectionWarning,
                )
                return False

            # undefined section
            section_var = _str_to_var(extracted_section_name)
            section = UndefinedSection(
                section_name=extracted_section_name,
            )
            setattr(self.target, section_var, section)

        # make sure section is in target._slots
        self.target._set_structure_items(
            items=section, positions=None, exist_action="ignore", slots=self.slots
        )
        # add slot to section
        section._add_slots(keys=self.slots, exist_ok=True)

        return section

    def _extract_option(self) -> Option | None:
        """Extract an option if present in self.current_entity_content.

        Returns:
            Option | None: The extracted option or None if no option was found
                in self.current_entity_content.
        """
        if (
            not self.possible_continuation
            or "option_delimiter" not in self.parameters.multiline_ignore
        ):
            with contextlib.suppress(ExtractionError):
                return Option.from_string(
                    string=self.current_entity_content,
                    delimiter=self.parameters.option_delimiters,
                    type_converter=self.parameters.default_type_converter,
                    slots=self.slots,
                )
        return None

    def _handle_option(
        self,
        extracted_option: Option,
    ) -> UndefinedOption | Option | None | Literal[False]:
        """Handle an extracted Option.

        Args:
            extracted_option (Option): Extracted option to handle.

        Returns:
            UndefinedOption | Option | None | False: The final Option in the section
                (differs from input) or None if Option could not be handled
                (e.g. due to undefined and undefined not allowed in parameters) or False
                if Option is undefined and to be ignored.
        """
        # check if Option is defined
        assert isinstance(self.current_section, Section)
        try:
            option = self.current_section._get_option(key=extracted_option.key)
            option._set_slots(
                value=extracted_option.iloc[-1][1],
                slots=self.slots,
                create_missing_slots=True,
            )
            self.current_section._set_structure_items(
                items=option, positions=None, exist_action="ignore", slots=self.slots
            )
        except EntityNotFound:
            # Option is undefined
            if self.parameters.read_undefined in {True, "option"} or (
                self.parameters.read_undefined == "section"
                and isinstance(self.current_section, UndefinedSection)
            ):
                # create UndefinedOption
                option = self.current_section._add_entity(
                    extracted_option, slots=self.slots
                )
            else:
                warnings.warn(
                    f"Line {self.current_entity_index} is being ignored because it's not a defined option (read_undefined is set to {self.parameters.read_undefined}).",
                    UndefinedOptionWarning,
                )
                return False

        return option

    def _extract_comment(self) -> Comment | None:
        """Extract an comment if present in self.current_entity_content.

        Returns:
            Comment | None: The extracted comment or None if no comment
                was found in line.
        """
        if (
            not self.possible_continuation
            or "comment_prefix" not in self.parameters.multiline_ignore
        ):
            with contextlib.suppress(ExtractionError):
                return Comment(
                    prefix=self.parameters.comment_prefixes,
                    content_with_prefix=self.current_entity_content,
                )
        return None

    def _handle_comment(self, extracted_comment: Comment) -> Comment:
        """Handle an extracted Comment (add it to current section if necessary).

        Args:
            extracted_comment (Comment): Extracted comment to handle.

        Returns:
            Comment: The comment added to the section
                (as of now the input Comment object).

        """
        assert isinstance(self.current_section, Section)
        self.current_section._add_entity(
            extracted_comment, positions=None, slots=self.slots
        )
        return extracted_comment

    def _check_for_possible_continuation(self) -> tuple[str, bool]:
        """Determine whether self.current_entity_content is a
        possible continuation of a multiline and remove multiline prefix from it.

        Returns:
            tuple[str, bool]: The new possible_continuation and current_entity_content.
        """
        possible_continuation = False
        current_entity_content = self.current_entity_content
        if (
            self.parameters.multiline_allowed
            and self.current_option
            and (
                continuation := re.search(
                    rf"(?<=^{self.parameters.multiline_prefix}).*",
                    self.current_entity_content,
                )
            )
        ):
            # (if no current option it can't be a continuation)
            possible_continuation = True
            current_entity_content = continuation[0]
        return current_entity_content, possible_continuation

    def _handle_continuation(self) -> None:
        """Handles a continuation (adds it to the last option)."""
        if self.possible_continuation:
            # add continuation to last option
            assert isinstance(self.current_option, Option)
            self.current_option.add_continuation(
                continuation=self.current_entity_content,
                type_converter=self.parameters.default_type_converter,
                slots=self.slots,
            )
        elif self.current_option is None:
            warnings.warn(
                f"Line {self.current_entity_index} is being ignored because it's invalid.",
                IniStructureWarning,
            )
        elif not self.parameters.multiline_allowed:
            warnings.warn(
                f"Line {self.current_entity_index} is being ignored because it's multiline to {f"'{self.current_option.key}'" if self.current_option else "an undefined option"} (multiline_allowed is set to {self.parameters.multiline_allowed}).",
                MultilineWarning,
            )

    def _is_empty_entity(self) -> bool:
        """Check whether self.current_entity_content qualifies as empty."""
        return bool(
            re.fullmatch(
                r"[\s\t]*" if self.parameters.ignore_whitespace_lines else r"",
                self.current_entity_content,
            )
        )


class SlotView:
    """Parent class for slot access."""

    def __init__(self, target: Schema | Section) -> None:
        """
        Args:
            target (Schema | Section): The target that is accessed.
        """
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
        access_kwargs = [
            k for k, v in get_type_hints(access_target).items() if v == SlotAccess
        ]

        def accessor_func(*args, **kwargs):
            for access_kwarg in access_kwargs:
                kwargs[access_kwarg] = slot
            return access_target(*args, **kwargs)

        return accessor_func

    def _set_slot(self, name: str, value: Any, slot: SlotAccess) -> None:
        """Set the slot(s) of an option.

        Args:
            name (str): Variable name of the option.
            value (Any): The new option value.
            slot (SlotAccess): Slot(s) to set.

        Raises:
            AttributeError: If any other than in option is tried to be set.
        """
        target, attr = super().__getattribute__("_get_target_attr")(name)
        if not (isinstance(attr, Option) and isinstance(target, Section)):
            raise AttributeError("Assignment only valid for options.")
        super().__getattribute__("_slot_access")(
            access_target=target._set_option, slot=slot
        )(name=name, value=value)

    def _get_target_attr(self, name: str) -> tuple[Schema | Section, Any]:
        """Get target of the SlotView and an attribute of the target.

        Args:
            name (str): Variable name of the attribute.

        Returns:
            tuple[Schema | Section, Any]: Target and the attribute.
        """
        target = super().__getattribute__("_target")
        attr = target.__dict__.get(name, None) or getattr(target, name)
        return (target, attr)


class SlotDecider(SlotView):
    """Gives access to slots by deciding."""

    def __init__(
        self, target: Schema | Section, slots: Slots, decider_method: SlotDeciderMethods
    ) -> None:
        """
        Args:
            target (Schema | Section): The target to prepare for slot access.
            slots (Slots): The slots to take as reference.
            decider_method (SlotDeciderMethods): The method to use for decision.
        """
        super().__init__(target=target)
        super().__setattr__("_decider_method", decider_method)
        super().__setattr__("_slots", slots)

    def __getattribute__(self, name: str) -> Any:
        target, attr = super().__getattribute__("_get_target_attr")(name)

        if isinstance(attr, Option):
            return super().__getattribute__("_decide_slot")(attr)[1].converted
        elif isinstance(attr, Section):
            return SlotDecider(
                attr,
                super().__getattribute__("_slots"),
                super().__getattribute__("_decider_method"),
            )
        elif (
            not name.startswith("__")
            and callable(attr)
            and SlotAccess in get_type_hints(attr).values()
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
        OptionSlotValue | Structure,
    ]:
        """Decides, which slot to access using the defined decider method.

        Args:
            target (Option | Section): The Option or Section that is to be accessed.

        Returns:
            tuple[SlotKey, OptionSlotValue | SectionStructure]: Tuple of the target's
                decided slot's key and value.

        """
        decider_method: SlotDeciderMethods = super().__getattribute__("_decider_method")
        slots: Slots = super().__getattribute__("_slots")

        return super().__getattribute__("_decision")(
            target=target, reference_slots=slots, method=decider_method
        )

    @classmethod
    def _decision(
        cls,
        target: Option | Section,
        reference_slots: Slots,
        method: SlotDeciderMethods,
    ) -> tuple[
        SlotKey,
        OptionSlotValue | Structure,
    ]:
        """Decides, which slot to access using the passed decider method and the passed
        reference slots.

        Args:
            target (Option | Section): The Option or Section that is to be accessed.
            reference_slots (Slots): Slots to use as reference.
            method (SlotDeciderMethods): The method to use for decision making.

        Returns:
            tuple[SlotKey, OptionSlotValue | SectionStructure]: Tuple of the target's
                decided slot's key and value.

        """
        latest_key = reference_slots.iloc[-1][0]
        first_key = reference_slots.iloc[0][0]

        match method:
            case "fallback":
                latest_val = target._get_slots(latest_key)
                return (
                    (latest_key, latest_val)
                    if latest_val is not None
                    else (first_key, target._get_slots(first_key))
                )
            case "first":
                return first_key, target._get_slots(first_key)
            case "cascade up":
                return next((k, v) for k, v in target._slots.items() if v is not None)
            case "latest":
                return latest_key, target._get_slots(latest_key)
            case "cascade down":
                return next(
                    (k, v) for k, v in reversed(target._slots.items()) if v is not None
                )


class SlotViewer(SlotView):
    """Gives access to a specific slot."""

    def __init__(
        self,
        target: Schema | Section,
        slot: SlotAccess,
    ) -> None:
        """
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
            out = attr[slot]
            if isinstance(out, list):
                return [val.converted for val in out]
            return out.converted

        # Schema[].Section.(SlotAccess)
        elif callable(attr):
            return super().__getattribute__("_slot_access")(attr, slot)

        return attr

    def __setattr__(self, name: str, value: Any) -> None:
        slot: SlotAccess = super().__getattribute__("_slot")
        super().__getattribute__("_set_slot")(name, value, slot)


class SlotIlocViewer(SlotView):
    """Gives access to a specific slot by index."""

    def __init__(
        self,
        target: Schema,
    ) -> None:
        """
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
