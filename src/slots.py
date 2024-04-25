"""Classes related to slot mechanism"""
from typing import Literal, Callable    
DeciderMethods = Literal["default", "latest"]

type Slots = list
type SlotAccess = int | list[int] | None