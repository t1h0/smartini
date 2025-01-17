"""SmartIni's slot logic."""

from typing import (
    Literal,
    overload,
    Callable,
    Generator,
    Any,
    Sequence,
)
from .utils import OrderedDict
from .exceptions_warnings import (
    SlotNotFound,
    SlotAlreadyExists,
    DuplicateEntityError,
)

type SlotDeciderMethods = Literal[
    "fallback", "first", "cascade up", "latest", "cascade down"
]
"""Method to decide which slot to use.
    "fallback": Uses first slot whenever latest slot is None, otherwise latest slot.
        This is especially useful if the first slot provides default fallback values
        for your configuration.
    "first": Uses first slot.
    "cascade up": Uses the first slot that is not None from first to latest.
    "latest": Uses latest slot.
    "cascade down": Uses first slot that is not None from latest to first.    
"""

type SlotKey = int | str
type SlotAccess = SlotKey | list[SlotKey] | None
"""Identifier for which slot(s) to access. int or str identifier for a single slot,
list[SlotKey] for multiple slots and None for all slots.
"""


class Slots[SlotValue](OrderedDict[SlotKey, SlotValue]):
    """Container for slots."""

    def __init__(self, value_type: type[SlotValue], *args, **kwargs) -> None:
        """
        Args:
            value_type (type[SlotValue]): Type this container's values should have.
        """
        self._value_type = value_type
        super().__init__(*args, **kwargs)

    @overload
    def __getitem__(self, slots: None | list) -> list[SlotValue]: ...

    @overload
    def __getitem__(self, slots: SlotKey) -> SlotValue: ...

    def __getitem__(self, slots: SlotAccess) -> list[SlotValue] | SlotValue:
        if slots is None:
            return list(self.values())
        try:
            if isinstance(slots, list):
                return [super().__getitem__(slot) for slot in slots]
            else:
                return super().__getitem__(slots)
        except KeyError as e:
            raise SlotNotFound(f"Slot(s) '{slots}' doesn't/don't exist.") from e

    def add(self, keys: SlotAccess, exist_ok=False) -> None:
        """Add new slots with self._value_type values.

        Args:
            keys (SlotAccess): The keys of the new slots.
            exist_ok (bool, optional): If True, won't raise an error
                if a key already exists. Defaults to False.
        """
        if keys is None:
            return
        for key in keys if isinstance(keys, list) else (keys,):
            if key in self:
                if not exist_ok:
                    raise IndexError(
                        f"Can't add slot with key '{key}' because it already exists."
                    )
            else:
                self[key] = (
                    self._value_type if self._value_type is None else self._value_type()
                )

    def slot_access(
        self, slot_access: SlotAccess, verify: bool | None = None
    ) -> list[SlotKey]:
        """Normalize slot_access to an iterable with slot keys.

        Args:
            slot_access (SlotAccess): The SlotAccess to normalize.
            verify (bool | None, optional): Will verify that all the requested slots
                slots exist (True) or don't exist (False). Won't if None.
                Defaults to None.
        Returns:
            Iterable[SlotKey]: Iterable with slot keys.
        """
        if slot_access is None:
            slots = list(self.keys())
        else:
            slots = slot_access if isinstance(slot_access, list) else [slot_access]
            if verify is True and (diff := set(slots).difference(self.keys())):
                raise SlotNotFound(
                    f"Slot(s) '{",".join(str(d) for d in diff)}' doesn't/don't exist(s)."
                )
            elif verify is False and (inter := set(slots).intersection(self.keys())):
                raise SlotAlreadyExists(
                    f"Slot(s) '{",".join(str(d) for d in inter)}' already exist(s)."
                )
        return slots

    def set_slots(
        self,
        values: SlotValue | list[SlotValue] | Callable[[], SlotValue],
        create_missing_slots=False,
        *,
        slots: SlotAccess = None,
    ) -> None:
        """Set the content of specified slots.

        Args:
            values (SlotValue | list[SlotValue] | Callable[[],SlotValue]): New values,
                one per slot. If Callable, will call it len(slots) times and assign
                the return values accordingly.
            create_missing_slots (bool, optional): Whether to create slots that are
                specified but don't exist in the entity. Defaults to False.
            slots (SlotAccess, optional): Slots to set. Defaults to None.
        """
        slots = self.slot_access(slots)

        # verify values
        if callable(values):
            values_per_slot = [values() for _ in range(len(slots))]
        elif not isinstance(values, list):
            values_per_slot = [values]
        else:
            values_per_slot = values

        # check if we have one value per slot
        if len(slots) != len(values_per_slot):
            if len(slots) != 1:
                raise ValueError(
                    f"Number of values ({len(values_per_slot)}) doesn't match number of slots ({len(slots)})."
                )
            # one slot, interpret the list as one value for the slot
            values_per_slot = [values_per_slot]

        for slot, value in zip(self.slot_access(slots), values_per_slot):
            if slot not in self:
                if not create_missing_slots:
                    raise IndexError(
                        f"Slot '{slot}' can't be set because it doesn't exist."
                    )
                self.add(slot)
            self[slot] = value


class _SlotEntity[SlotValue]:
    """Entity which implements slots to save different values."""

    def __init__(self, slot_value: type[SlotValue]) -> None:
        """
        Args:
            slot_value (type[Slot]): Type of the values this entity's slots should have.
        """
        self._slots = Slots(slot_value)
        self.iloc = self._slots.iloc

    @property
    def _nslot(self) -> int:
        """Number of slots for this entity.

        Note: Private (underscore) property added for compatibility with interface objects
        that have _nslot properties.

        Returns:
            int: The number of slots for this entity.
        """
        return len(self._slots)

    @property
    def nslot(self) -> int:
        """Number of slots for this entity.

        Returns:
            int: The number of slots for this entity.
        """
        return self._nslot

    def _add_slots(self, keys: SlotAccess, exist_ok=False) -> None:
        """Add new slots with self._value_type values.

        Args:
            keys (SlotAccess): The keys of the new slots.
            exist_ok (bool, optional): If True, won't raise an error
                if a key already exists. Defaults to False.
        """
        self._slots.add(keys, exist_ok)

    def _set_slots(
        self,
        value: Callable[[], SlotValue],
        create_missing_slots=False,
        *,
        slots: SlotAccess = None,
    ) -> None:
        """Set the content of specified slots.

        Args:
            value (Callable[[], SlotValue]): Will call len(slots) times and assign the
                return values accordingly.
            create_missing_slots (bool, optional): Whether to create slots that are
                specified but don't exist in the entity. Defaults to False.
            slots (SlotAccess, optional): Slots to set. Defaults to None.
        """
        return self._slots.set_slots(
            values=value,
            create_missing_slots=create_missing_slots,
            slots=slots,
        )

    @overload
    def __getitem__(self, slots: None | list) -> list[SlotValue]: ...

    @overload
    def __getitem__(self, slots: SlotKey) -> SlotValue: ...

    def __getitem__(self, slots: SlotAccess) -> list[SlotValue] | SlotValue:
        return self._slots[slots]

    def _get_slots(self, slots: SlotAccess, default: Any = None) -> Any:
        try:
            return self._slots[slots]
        except SlotNotFound:
            return default


class Structure[StructureItem](list[StructureItem]):
    """Structure saving the order of entities."""

    def validate_position(self, pos: int) -> bool:
        """Verify that a position in the structure can be accessed.

        Args:
            pos (int): The position

        Returns:
            bool: Whether pos is inside the structure's boundaries or one above
                (to add).
        """
        l = len(self)
        return -l - 1 <= pos <= l


class _StructureSlotEntity[StructureItem](_SlotEntity[Structure[StructureItem]]):
    """Entity that has a Structure in each slot."""

    def __init__(self) -> None:
        # contains the initial structure as saved in schema definition
        self._schema_structure = Structure()

        super().__init__(Structure)

    @overload
    def _get_items[
        DefinedItem, UndefinedItem
    ](
        self,
        defined_item: type[DefinedItem],
        undefined_item: type[UndefinedItem],
        include_undefined: Literal[False] = ...,
        *,
        slots: SlotAccess = None,
    ) -> OrderedDict[str, DefinedItem]: ...
    @overload
    def _get_items[
        DefinedItem, UndefinedItem
    ](
        self,
        defined_item: type[DefinedItem],
        undefined_item: type[UndefinedItem],
        include_undefined: Literal[True] = True,
        *,
        slots: SlotAccess = None,
    ) -> OrderedDict[str, DefinedItem | UndefinedItem]: ...
    @overload
    def _get_items[
        DefinedItem, UndefinedItem
    ](
        self,
        defined_item: type[DefinedItem],
        undefined_item: type[UndefinedItem],
        include_undefined: Literal["only"] = ...,
        *,
        slots: SlotAccess = None,
    ) -> OrderedDict[str, UndefinedItem]: ...

    def _get_items[
        DefinedItem, UndefinedItem
    ](
        self,
        defined_item: type[DefinedItem],
        undefined_item: type[UndefinedItem],
        include_undefined: bool | Literal["only"] = True,
        *,
        slots: SlotAccess = None,
    ) -> (
        OrderedDict[str, DefinedItem | UndefinedItem]
        | OrderedDict[str, DefinedItem]
        | OrderedDict[str, UndefinedItem]
    ):
        """Get items of the entity.

        Args:
            defined_item (type[DefinedItem]): Type of the defined item.
            undefined_item (type[UndefinedItem]): Type of the undefined item.
            include_undefined (bool | "only", optional): Whether to include undefined
                items. If "only", will return only undefined items. Always False
                if slots is not None.
            slots (SlotAccess, optional): Which slot(s) to get items from. If multiple
                are given, will return the intersection. If None will return all.
                Defaults to None.

        Returns:
            OrderedDict[str, DefinedItem | UndefinedItem] | OrderedDict[str, DefinedItem]
                | OrderedDict[str, UndefinedItem]: Variable names as keys and items as
                values. Order is that of the slot structure if len(slots) == 1.
                Otherwise, order matches original schema structure with undefined items
                at the end.
        """
        valid_item = (
            (lambda x: isinstance(x, undefined_item))
            if include_undefined == "only"
            else (
                (lambda x: isinstance(x, defined_item))
                if include_undefined
                else (
                    lambda x: isinstance(x, defined_item)
                    and not isinstance(x, undefined_item)
                )
            )
        )

        if slots is None:
            return OrderedDict(
                {name: var for name, var in vars(self).items() if valid_item(var)}
            )

        slots_access = self._slots.slot_access(slots)

        if len(slots_access) == 1:
            # return items in order of slot structure
            return OrderedDict(
                {
                    k: v
                    for item in self._slots[slots_access][0]
                    if valid_item(item)
                    for k, v in vars(self).items()
                    if v == item
                }
            )

        items_intersection = {
            item for slot in self._slots[slots_access] for item in slot
        }

        # return items in order of original schema structure
        return OrderedDict(
            {
                name: var
                for name, var in vars(self).items()
                if valid_item(var) and var in items_intersection
            }
        )

    def _set_structure_items(
        self,
        items: StructureItem | list[StructureItem],
        positions: int | list[int | None] | None = None,
        exist_action: Literal[
            "exception", "ignore", "move", "move_not_None"
        ] = "exception",
        *,
        slots: SlotAccess = None,
    ) -> None:
        """Insert items into the structure.

        Args:
            items (StructureItem | list[StructureItem]): The item(s) to insert.
            positions (int | list[int | None] | None): Position in structure the item(s)
                should take. Either int for same position in all slots or one position
                per slot. If None and for every slot that None is specified as the
                position, will take previous position of the Option in the respective
                slot and will append to slots where Option didn't exist before. Defaults to None.
            exist_action ("exception" | "ignore" | "move" | "move_not_None", optional):
                What to do, when an item already exists in the structure. "exception"
                will raise an DuplicateEntityError, "ignore" will simply ignore the item,
                "move" will move the item to the specified position and "move_not_None"
                will only move an item, if the position for that slot is not None.
                Defaults to "exception".
            slots (SlotAccess, optional): Slot(s) to add the entity to.
                Must match positions. Defaults to None.
        """
        slots = self._slots.slot_access(slots, verify=True)
        validated_positions = self._validate_position(positions, slots)

        # define handling of duplicates
        handle_dupl = (
            (lambda pos: "ignore" if pos is None else "move")
            if exist_action == "move_not_None"
            else (lambda _: exist_action)
        )

        if not isinstance(items, list):
            items = [items]

        for s, pos in zip(slots, validated_positions):
            # define slice for inserting
            pos_slice = (
                slice(len(self._slots[s]), len(self._slots[s]))
                if pos is None
                else slice(pos, pos)
            )

            items_set = set(items)

            # check for duplicates
            if dupl := items_set.intersection(self._slots[s]):
                match handle_dupl(pos):
                    case "ignore":
                        self._slots[s][pos_slice] = items_set.difference(dupl)
                    case "move":
                        new_slot = []
                        for i, v in enumerate(self._slots[s]):
                            if i == pos_slice.start:
                                new_slot.extend(items)
                            if v not in dupl:
                                new_slot.append(v)
                    case _:  # includes "exception"
                        raise DuplicateEntityError(f"Items {dupl} already exist.")
            else:
                # no duplicates
                self._slots[s][pos_slice] = items

    def _set_structure(
        self,
        new_structure: Sequence[StructureItem],
        create_missing_slots: bool = False,
        *,
        slots: SlotAccess,
    ) -> None:

        if any(entity not in vars(self).values() for entity in new_structure):
            raise ValueError("Entities of new structure must all belong to section.")
        slots = self._slots.slot_access(slots)
        self._set_slots(
            create_missing_slots=create_missing_slots,
            value=lambda: Structure(new_structure),
            slots=slots,
        )

    @overload
    def _validate_position(
        self, position: int | list[int], slots: list[SlotKey]
    ) -> list[int]: ...
    @overload
    def _validate_position(
        self, position: None | list[None], slots: list[SlotKey]
    ) -> list[None]: ...
    @overload
    def _validate_position(
        self, position: list[int | None], slots: list[SlotKey]
    ) -> list[int | None]: ...

    def _validate_position(
        self,
        position: int | list[int] | None | list[None] | list[int | None],
        slots: list[SlotKey],
    ) -> list[int] | list[None] | list[int | None]:
        """Validate, that the requested position(s) can be accessed for the requested slot(s).

        Args:
            position (int | list[int] | None | list[None] | list[int | None]):
                The position(s) to access.
            slots (list[SlotKey]): The requested slots.

        Returns:
            list[int] | list[None] | list[int | None]: Requested positions, one per slot.
        """
        if isinstance(position, int):
            position = [position] * len(slots)

        if position is None:
            position = [None] * len(slots)
        else:
            if len(position) != len(slots):
                raise IndexError("Number of positions must match number of slots.")
            for s, pos in zip(slots, position):
                if pos is not None and not self._slots[s].validate_position(pos):
                    raise IndexError(
                        f"Can't insert into slot {s} at position {pos} because slot is too small."
                    )
        return position
