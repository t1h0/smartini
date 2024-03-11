"""Proxies contain the actual ini content."""

from dataclasses import dataclass, field
from src.entities import Comment, Option, OptionKey, SectionName
from src.nomotools.collections import OrderedDict


@dataclass
class SectionProxy:
    """Contains a section's content."""

    name: SectionName | None
    structure: list[Comment | Option] = field(default_factory=list)
    options: OrderedDict[OptionKey, Option] = field(default_factory=OrderedDict)


@dataclass
class IniProxy:
    """Contains an ini's content."""

    sections: OrderedDict[SectionName | None, SectionProxy] = field(
        default_factory=OrderedDict
    )
