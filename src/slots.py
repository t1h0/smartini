"""Classes related to slot mechanism"""

from typing import Literal, TypeVar, overload, Callable, Generator, Any, Sequence
from nomopytools.collections_extensions import OrderedDict
from src.exceptions import (
    SlotNotFound,
    SlotAlreadyExists,
    IniStructureError,
    DuplicateEntityError,
)

T = TypeVar("T")

SlotDeciderMethods = Literal["default", "first", "cascade up", "latest", "cascade down"]
"""Method to decide which slot to use.
    "default": Uses first slot whenever latest slot is None, otherwise latest slot.
    "first": Uses first slot.
    "cascape up": Uses the first slot that is not None from first to latest.
    "latest": Uses latest slot.
    "cascade down": Uses first slot that is not None from latest to first.    
"""

SlotKey = int | str
SlotValue = TypeVar("SlotValue")
SlotAccess = int | str | list[int | str] | None
"""Which slot to access. Int or str identifier for a single slot, list[int|str] for
multiple slots and None for all slots.
"""


class Slots(OrderedDict[SlotKey, SlotValue]):

    def __init__(self, value_type: type[SlotValue], *args, **kwargs) -> None:
        """Container for slot objects.

        Args:
            value_type (type[SlotValue]): Type this container's values should have.
        """
        self._value_type = value_type
        super().__init__(*args, **kwargs)

    @overload
    def __getitem__(self, slots: None | list) -> list[SlotValue]: ...

    @overload
    def __getitem__(self, slots: int | str) -> SlotValue: ...

    def __getitem__(self, slots: SlotAccess) -> list[SlotValue] | SlotValue | None:
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
                        "Can't add slot with key '{key}' because it already exists."
                    )
            else:
                self[key] = (
                    self._value_type if self._value_type is None else self._value_type()
                )

    def slot_access(
        self, slot_access: SlotAccess, verify: bool | None = None
    ) -> list[int | str]:
        """Normalize slot_access to an iterable with slot keys.

        Args:
            slot_access (SlotAccess): The SlotAccess to normalize.
            verify (bool | None, optional): Will verify that all the requested slots
                slots exist (True) or don't exist (False). Won't if None.
                Defaults to None.
        Returns:
            Iterable[int | str]: Iterable with slot keys.
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
        new_slot_value: SlotValue | None = None,
        create_missing_slots=False,
        *,
        slots: SlotAccess = None,
        **kwargs,
    ) -> None:
        """Set the content of specified slots.

        Args:
            new_slot_value (SlotValue | None, optional): New value all slots should take.
                If None, will access kwargs. Defaults to None.
            slots (SlotAccess, optional): Slots to set. Defaults to None.
            create_missing_slots (bool, optional): Whether to create slots that are
                specified but don't exist in the entity. Defaults to False.
            **kwargs: Keyword-arguments to set, corresponding to entity slot attributes.
        """
        for slot in self.slot_access(slots):
            if slot not in self:
                if not create_missing_slots:
                    raise IndexError(
                        f"Slot '{slot}' can't be set because it doesn't exist."
                    )
                # warnings.warn(warn.slot_manipulation)
                self.add(slot)
            if new_slot_value is None:
                slot_object = self[slot]
                for k, v in kwargs.items():
                    setattr(slot_object, k, v)
            else:
                self[slot] = new_slot_value


class SlotEntity[SlotValue]:

    def __init__(self, slot_value: type[SlotValue]) -> None:
        """Entity which implements slots to save different values.

        Args:
            slot_value (type[Slot]): Type of the values this entity's slots should have.
        """
        self._slots = Slots(slot_value)
        self.iloc = self._slots.iloc

    @property
    def _nslot(self) -> int:
        """Number of slots for this entity.

        Note: Private (underscore) property added for compability with interface objects
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
        new_slot_value: SlotValue | None = None,
        create_missing_slots=False,
        *,
        slots: SlotAccess = None,
        **kwargs,
    ) -> None:
        """Set the content of specified slots.

        Args:
            new_slot_value (SlotValue | None, optional): New value all slots should take.
                If None, will access kwargs. Defaults to None.
            slots (SlotAccess, optional): Slots to set. Defaults to None.
            create_missing_slots (bool, optional): Whether to create slots that are
                specified but don't exist in the entity. Defaults to False.
            **kwargs: Keyword-arguments to set, corresponding to entity slot attributes.
        """
        return self._slots.set_slots(
            new_slot_value=new_slot_value,
            create_missing_slots=create_missing_slots,
            slots=slots,
            **kwargs,
        )

    @overload
    def __getitem__(self, slots: None | list) -> list[SlotValue]: ...

    @overload
    def __getitem__(self, slots: int | str) -> SlotValue: ...

    def __getitem__(self, slots: SlotAccess) -> list[SlotValue] | SlotValue | None:
        return self._slots[slots]

    def __setitem__(self, slots: SlotAccess, value: Any) -> None:
        self._slots.set_slots(value=value, slots=slots)

    def _get_slots(self, slots: SlotAccess, default: Any = None) -> Any:
        try:
            return self._slots[slots]
        except SlotNotFound:
            return default

    @overload
    def _apply_to_slots(
        self,
        func: Callable[[SlotValue], T],
        _id: None = ...,
        inplace: Literal[False] = ...,
        *,
        slots: SlotAccess = None,
    ) -> Generator[T, None, None]: ...
    @overload
    def _apply_to_slots(
        self,
        func: Callable[[int, SlotValue], T],
        _id: Literal["index"] = ...,
        inplace: Literal[False] = ...,
        *,
        slots: SlotAccess = None,
    ) -> Generator[T, None, None]: ...
    @overload
    def _apply_to_slots(
        self,
        func: Callable[[SlotKey, SlotValue], T],
        _id: Literal["key"] = ...,
        inplace: Literal[False] = ...,
        *,
        slots: SlotAccess = None,
    ) -> Generator[T, None, None]: ...
    @overload
    def _apply_to_slots(
        self,
        func: Callable[[SlotKey, int, SlotValue], T],
        _id: Literal["both"] = ...,
        inplace: Literal[False] = ...,
        *,
        slots: SlotAccess = None,
    ) -> Generator[T, None, None]: ...
    @overload
    def _apply_to_slots(
        self,
        func: Callable[[SlotValue], SlotValue],
        _id: None = ...,
        inplace: Literal[True] = ...,
        *,
        slots: SlotAccess = None,
    ) -> None: ...
    @overload
    def _apply_to_slots(
        self,
        func: Callable[[int, SlotValue], SlotValue],
        _id: Literal["index"] = ...,
        inplace: Literal[True] = ...,
        *,
        slots: SlotAccess = None,
    ) -> None: ...
    @overload
    def _apply_to_slots(
        self,
        func: Callable[[SlotKey, SlotValue], SlotValue],
        _id: Literal["key"] = ...,
        inplace: Literal[True] = ...,
        *,
        slots: SlotAccess = None,
    ) -> None: ...
    @overload
    def _apply_to_slots(
        self,
        func: Callable[[SlotKey, int, SlotValue], SlotValue],
        _id: Literal["both"] = ...,
        inplace: Literal[True] = ...,
        *,
        slots: SlotAccess = None,
    ) -> None: ...

    def _apply_to_slots(
        self,
        func: (
            Callable[[SlotValue], T]
            | Callable[[int, SlotValue], T]
            | Callable[[SlotKey, SlotValue], T]
            | Callable[[SlotKey, int, SlotValue], SlotValue]
            | Callable[[SlotValue], SlotValue]
            | Callable[[int, SlotValue], SlotValue]
            | Callable[[SlotKey, SlotValue], SlotValue]
            | Callable[[SlotKey, int, SlotValue], SlotValue]
        ),
        _id: Literal["key", "index", "both"] | None = None,
        inplace=False,
        *,
        slots: SlotAccess = None,
    ) -> Generator[T, None, None] | Generator[SlotValue, None, None] | None:
        """Apply function to slots.

        Args:
            func (Callable): Function to apply.
            _id ("key" | "index" | "both" | None], optional): Whether the applied
                function takes as input only the slot value (None) or additionally as
                the first argument the slot key ("key") or the slot index ("index") or
                both ("both", with first argument key, second index, third the value).
                Defaults to None.
            inplace (bool, optional): Whether to apply the function inplace.
                Defaults to False
            slots (SlotAccess, optional): Slots to apply the function to.
                Defaults to None (all slots).

        Returns:
            Generator | None: Generator for each slot or None if inplace is True.
        """
        slots = self._slots.slot_access(slot_access=slots, verify=True)
        match _id:
            case "key":
                gen = (
                    func(key, slot) for key, slot in self._slots.items() if key in slots
                )
            case "index":
                gen = (
                    func(index, slot)
                    for index, (key, slot) in enumerate(self._slots.items())
                    if key in slots
                )
            case "both":
                gen = (
                    func(key, index, slot)
                    for index, (key, slot) in enumerate(self._slots.items())
                    if key in slots
                )
            case _:
                gen = (func(slot) for slot in self[slots])
        if not inplace:
            return gen
        for key, val in zip(self._slots, gen):
            self._slots[key] = val


StructureItem = TypeVar("StructureItem")


class Structure[StructureItem](list[StructureItem]):

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


class StructureSlotEntity[StructureItem](SlotEntity[Structure[StructureItem]]):

    def __init__(self) -> None:
        super().__init__(Structure)

    def _insert_structure_items(
        self,
        items: StructureItem | list[StructureItem],
        positions: int | list[int] | None = None,
        exist_ok: bool = False,
        *,
        slots: SlotAccess = None,
    ) -> None:
        """Insert items into the struture.

        Args:
            items (StructureItem | list[StructureItem]): The item(s) to insert.
            positions (int | list[int | None], optional): Where to put the item(s) in
                the structure. Either one position for all slots or a list
                with one position per slot. If None, will append to the end in every slot.
                Defaults to None.
            exist_ok (bool, optional): Whether to not throw an error if the item already
                exists in the structure. If True, will simply not insert the item.
                Defaults to False.
            slots (SlotAccess, optional): Slot(s) to add the entity to.
                Must match positions. Defaults to None.
        """
        slots = self._slots.slot_access(slots, verify=True)
        if positions is not None:
            positions = self._validate_position(positions, slots)
        if not isinstance(items, list):
            items = [items]
        for s, pos in zip(slots, positions):
            if (dupl := set(items).intersection(self._slots[s])) and not exist_ok:
                raise DuplicateEntityError(f"Items {dupl} already exist.")
            if positions is None:
                self._slots[s].extend(
                    item for item in items if item not in self._slots[s]
                )
            else:
                self._slots[s][pos:pos] = (
                    item for item in items if item not in self._slots[s]
                )

    def _set_structure(
        self,
        new_structure: Sequence[StructureItem],
        create_missing_slots: bool = False,
        *,
        slots: SlotAccess,
    ) -> None:

        if any(entity not in vars(self).values() for entity in new_structure):
            raise IniStructureError(
                "Entities of new structure must all belong to section."
            )
        self._set_slots(
            create_missing_slots=create_missing_slots,
            new_slot_value=Structure(new_structure),
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
        position: int | None | list[int] | list[None] | list[int | None],
        slots: list[SlotKey],
    ) -> list[int] | list[None] | list[int | None]:
        """Validate, that the requested position(s) can be accessed for the requested slot(s).

        Args:
            position (int | None | list[int] | list[None] | list[int  |  None]):
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
