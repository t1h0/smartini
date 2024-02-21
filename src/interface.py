from _collections_abc import ItemsView, KeysView, ValuesView
from configparser import ConfigParser
from pathlib import Path
from typing import Any

def initialize(default: str | Path, user: str | Path) -> None:
    """Read a default ini and update it with a user ini as long as the user ini's keys
    have valid values (invalid user keys will be ignored).

    Args:
        default (str | Path): Path to the default ini.
        user (str | Path): Path to the user ini.
    """
    global CONFIG

    cfg = ConfigParser()
    cfg.read(default)

    user_cfg = ConfigParser()
    user_cfg.read(user)

    # remove empty user ini entries
    for sec in user_cfg.sections():
        for opt, val in user_cfg.items(sec):
            if not val:
                user_cfg.remove_option(sec, opt)

    # update default values with user values
    cfg.update(user_cfg)

    CONFIG = cfg


def _access_ini(section, option):
    if "CONFIG" not in globals():
        raise RuntimeError("No config files loaded. Use initialize() first.")
    if CONFIG.has_option(section, option) and (opt := CONFIG.get(section, option)):
        return opt
    raise ValueError()
    


class _SectionMeta(type):
    """Metaclass for ini configuration file sections. Section names must be specified
    via '_name' class variable. Allows for values of section attributes to be retrieved
    like SECTION.ATTRIBUTE."""

    def __new__(cls, name, bases, attrs):
        if bases and Section in bases and "_name" not in attrs:
            raise AttributeError(
                f"Class '{name}' must define section name as '_name' class attribute."
            )
        return super().__new__(cls, name, bases, attrs)

    def __getattribute__(cls, name) -> str:
        section = super().__getattribute__("_name")
        if name == "_name":
            return section
        option = super().__getattribute__(name)
        if callable(option):
            return option
        return _access_ini(section, option)


class Section(metaclass=_SectionMeta):
    """Class for ini configuration file sections. Keys will be ini keys, and values the
    ini values, the same with items. Name of the section must be defined via
    '_name' class attribute.
    """

    # name of the section. must be provided!
    _name: str

    @classmethod
    def keys(cls) -> KeysView:
        return CONFIG[cls._name].keys()

    @classmethod
    def values(cls) -> ValuesView:
        return CONFIG[cls._name].values()

    @classmethod
    def items(cls) -> ItemsView:
        return CONFIG[cls._name].items()

    @classmethod
    def get(cls, key: str, fallback: Any = None) -> Any:
        return CONFIG[cls._name].get(key, fallback)

    @classmethod
    def to_dict(cls) -> dict[str, str]:
        return dict(CONFIG[cls._name].items())
