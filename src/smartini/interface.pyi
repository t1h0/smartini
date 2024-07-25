from typing import overload, Literal, Self
import re
from pathlib import Path
from .slots import SlotAccess, SlotKey, SlotDeciderMethods
from .entities import Option, OptionValue, UndefinedOption, Comment, SectionName
from .args import Parameters
from .utils import OrderedDict

class Section:

    # name of the section if actual section name differs from class variable
    _name: str | None

    @overload
    @classmethod
    def _add_entity(
        cls,
        entity: UndefinedOption | Option,
        positions: int | list[int | None] | None = None,
        *,
        slots: SlotAccess = None,
    ) -> UndefinedOption: ...
    @overload
    @classmethod
    def _add_entity(
        cls,
        entity: Comment,
        positions: int | list[int | None] | None = None,
        *,
        slots: SlotAccess = None,
    ) -> Comment: ...
    @overload
    @classmethod
    def add_entity(
        cls,
        entity: UndefinedOption | Option,
        positions: int | list[int] | None = None,
        *,
        slots: SlotAccess = None,
    ) -> UndefinedOption: ...
    @overload
    @classmethod
    def add_entity(
        cls,
        entity: Comment,
        positions: int | list[int] | None = None,
        *,
        slots: SlotAccess = None,
    ) -> Comment:
        """Add a new entity to the section.

        Args:
            entity (UndefinedOption | Option | Comment): The entity to add.
            positions (int | list[int | None], optional): Where to put the entity in
                the section's structure. Either one position for all slots or a list
                with one position per slot. If None, will append to the end in every slot.
                Defaults to None.
            slots (SlotAccess, optional): Slot(s) to add the entity to.
                Must match positions. Defaults to None.

        Returns:
            UndefinedOption | Comment: The newly created entity.
        """

    @overload
    @classmethod
    def _get_option(cls, name: str = ..., key: SlotKey | None = ...) -> Option: ...
    @overload
    @classmethod
    def _get_option(cls, name: None = ..., key: SlotKey = ...) -> Option: ...
    @overload
    @classmethod
    def get_option(cls, name: str = ..., key: SlotKey | None = ...) -> Option: ...
    @overload
    @classmethod
    def get_option(cls, name: None = ..., key: SlotKey = ...) -> Option:
        """Get an option by variable name or option key.

        Args:
            name (str | None, optional): Name of the option variable. Defaults to None.
            key (SlotKey | None, optional): The option key. Will be ignored if name is
                not None. Defaults to None.

        Returns:
            Option: The requested option.
        """

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
    @overload
    def get_options(
        self,
        include_undefined: Literal[False] = ...,
        *,
        slots: SlotAccess = None,
    ) -> OrderedDict[str, Option]: ...
    @overload
    def get_options(
        self,
        include_undefined: Literal[True] = True,
        *,
        slots: SlotAccess = None,
    ) -> OrderedDict[str, Option | UndefinedOption]: ...
    @overload
    def get_options(
        self,
        include_undefined: Literal["only"] = ...,
        *,
        slots: SlotAccess = None,
    ) -> OrderedDict[str, UndefinedOption]: ...
    def get_options(
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

    @overload
    @classmethod
    def _set_option(
        cls,
        name: str,
        value: OptionValue,
        positions: int | list[int | None] | None = None,
        key: ... = ...,
        *,
        slots: SlotAccess = None,
    ) -> None: ...
    @overload
    @classmethod
    def _set_option(
        cls,
        name: None,
        value: OptionValue,
        positions: int | list[int | None] | None = None,
        key: str = ...,
        *,
        slots: SlotAccess = None,
    ) -> None: ...
    @overload
    @classmethod
    def set_option(
        cls,
        name: str,
        value: OptionValue,
        positions: int | list[int | None] | None = None,
        key: ... = ...,
        *,
        slots: SlotAccess = None,
    ) -> None: ...
    @overload
    @classmethod
    def set_option(
        cls,
        name: None,
        value: OptionValue,
        positions: int | list[int | None] | None = None,
        key: str = ...,
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
            slots (SlotAccess, optional): The slot(s) to use. Defaults to None (all slots).
        """

    @classmethod
    def _get_comments_by_content(
        cls, content: str | re.Pattern
    ) -> dict[str, Comment]: ...
    @classmethod
    def get_comments_by_content(cls, content: str | re.Pattern) -> dict[str, Comment]:
        """Get comments matching the content.

        Args:
            content (str | re.Pattern): The content to search for.

        Returns:
            dict[str, Comment]: All comments that fit the content argument with variable
                names as keys and the Comment objects as values.
        """

    @classmethod
    def _get_comments(cls) -> dict[str, Comment]: ...
    @classmethod
    def get_comments(cls) -> dict[str, Comment]:
        """Get all comments of the section.

        Returns:
            dict[str, Comment]: Variable names as keys and Comments as values.
        """

class UndefinedSection(Section):
    def __init__(self, section_name: str | None) -> None: ...

class Schema:
    def __init__(
        self,
        parameters: Parameters | None = None,
        method: SlotDeciderMethods = "fallback",
        **kwargs,
    ) -> None: ...
    def __getitem__(self, key: SlotAccess) -> Self: ...
    @property
    def iloc(self) -> Self: ...
    @classmethod
    def _with_slot(cls, slot: SlotAccess) -> Self: ...
    @classmethod
    def with_slot(cls, slot: SlotAccess) -> Self:
        """Access the ini using a specific slot. Equivalent to item access via brackets
        (i.e. Schema[slot]).

        Args:
            slot (SlotAccess): The slot to use.
        """

    @classmethod
    def _get_section(
        cls, section_name: SectionName | str | None
    ) -> tuple[str, Section]: ...
    @classmethod
    def get_section(cls, section_name: SectionName | str | None) -> tuple[str, Section]:
        """Get a section by its name.

        Args:
            section_name (SectionName | str | None): The name of the section to get.

        Raises:
            EntityNotFound: If the section was not found by its name.

        Returns:
            tuple[str, Section]: Tuple of variable name and section object.
        """

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
    @overload
    def get_sections(
        self,
        include_undefined: Literal[False] = ...,
        *,
        slots: SlotAccess = None,
    ) -> OrderedDict[str, Section]: ...
    @overload
    def get_sections(
        self,
        include_undefined: Literal[True] = True,
        *,
        slots: SlotAccess = None,
    ) -> OrderedDict[str, Section | UndefinedSection]: ...
    @overload
    def get_sections(
        self,
        include_undefined: Literal["only"] = ...,
        *,
        slots: SlotAccess = None,
    ) -> OrderedDict[str, UndefinedSection]: ...
    def get_sections(
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

    @classmethod
    def _read_ini(
        cls,
        path: str | Path,
        parameters: Parameters | None = None,
        parameters_as_default: bool = False,
        *,
        slots: SlotAccess | Literal[False] = False,
        **kwargs,
    ) -> None: ...
    @classmethod
    def read_ini(
        cls,
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

    @classmethod
    def _export(
        cls,
        path: str | Path,
        structure: Literal["schema", "content"] | None = None,
        decider_method: SlotDeciderMethods | None = None,
        include_undefined: bool = True,
        export_comments: bool = False,
        *,
        content_slots: SlotAccess = None,
    ) -> None: ...
    @classmethod
    def export(
        cls,
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
