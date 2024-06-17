from typing import overload, Literal, Self
import re
from pathlib import Path
from src.slots import SlotAccess, SlotKey, SlotDeciderMethods
from src.entities import Option, UndefinedOption, Comment
from src.args import Parameters
from nomopytools.collections_extensions import OrderedDict

class SectionMeta(type):
    """Metaclass for ini configuration file sections. Section names must be specified
    via '_name' class variable.
    """

    # name of the section. must be provided!
    _name: str | None

class Section:
    """An ini configuration file section. Name of the section must be defined via
    'name' class attribute.
    """

    # name of the section. must be provided!
    _name: str | None

    @overload
    @classmethod
    def _add_entity(
        cls,
        entity: UndefinedOption | Option,
        positions: int | list[int] = -1,
        *,
        slots: SlotAccess = None,
    ) -> UndefinedOption: ...
    @overload
    @classmethod
    def _add_entity(
        cls,
        entity: Comment,
        positions: int | list[int] = -1,
        *,
        slots: SlotAccess = None,
    ) -> Comment: ...
    @overload
    @classmethod
    def add_entity(
        cls,
        entity: UndefinedOption | Option,
        positions: int | list[int] = -1,
        *,
        slots: SlotAccess = None,
    ) -> UndefinedOption: ...
    @overload
    @classmethod
    def add_entity(
        cls,
        entity: Comment,
        positions: int | list[int] = -1,
        *,
        slots: SlotAccess = None,
    ) -> Comment:
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
            key (SlotKey | None, optional): The option key. Defaults to None.
        Returns:
            Option: The requested option.
        """

    @overload
    @classmethod
    def _set_option(
        cls,
        name: str,
        positions: int | list[int | None] | None = None,
        key: ... = ...,
        *,
        slots: SlotAccess = None,
        **kwargs,
    ) -> None: ...
    @overload
    @classmethod
    def _set_option(
        cls,
        name: None,
        positions: int | list[int | None] | None = None,
        key: str = ...,
        *,
        slots: SlotAccess = None,
        **kwargs,
    ) -> None: ...
    @overload
    @classmethod
    def set_option(
        cls,
        name: str,
        positions: int | list[int | None] | None = None,
        key: ... = ...,
        *,
        slots: SlotAccess = None,
        **kwargs,
    ) -> None: ...
    @overload
    @classmethod
    def set_option(
        cls,
        name: None,
        positions: int | list[int | None] | None = None,
        key: str = ...,
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

    @classmethod
    def _get_options(
        cls, include_undefined: bool = True, *, slots: SlotAccess = None
    ) -> OrderedDict[str, Option]: ...
    @classmethod
    def get_options(cls) -> dict[str, Option]:
        """Get all options of the section.

        Returns:
            dict[str, Option]: Variable names as keys and Options as values.
        """

    @classmethod
    def _get_comment_by_content(
        cls, content: str | re.Pattern
    ) -> dict[str, Comment]: ...
    @classmethod
    def get_comment_by_content(cls, content: str | re.Pattern) -> dict[str, Comment]:
        """Get a comment by its content.

        Args:
            content (str | re.Pattern): The content of the comment.

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

class Schema:
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

    def __getitem__(self, key: SlotAccess) -> Self: ...
    @property
    def iloc(self) -> Self: ...
    @classmethod
    def _with_slot(cls, slot: SlotAccess) -> Self: ...
    @classmethod
    def with_slot(cls, slot: SlotAccess) -> Self:
        """Access the ini using a specific slot.

        Args:
            slot (SlotAccess): The slot to use.
        """

    @overload
    @classmethod
    def _get_sections(cls, filled_only: Literal[True] = ...) -> dict[str, Section]: ...
    @overload
    @classmethod
    def _get_sections(
        cls, filled_only: Literal[False] = ...
    ) -> dict[str, Section | SectionMeta]: ...
    @overload
    @classmethod
    def get_sections(cls, filled_only: Literal[True] = ...) -> dict[str, Section]: ...
    @overload
    @classmethod
    def get_sections(
        cls, filled_only: Literal[False] = ...
    ) -> dict[str, Section | SectionMeta]:
        """Get all sections of the ini.

        Args:
            filled_only (bool, optional): Whether to only return sections that have
                been filled with content already. Defaults to True.

        Returns:
            dict[str, Section] | dict[str, Section | SectionMeta]: Dicitonary with
                access (variable) names as keys and the Sections as values.
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
