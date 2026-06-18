from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Snapshot:
    name: str
    dataset: str
    creation: str = ""
    used: str = "0"
    referenced: str = "0"
    defer_destroy: bool = False
    holds: list[str] = field(default_factory=list)
    clones: list[str] = field(default_factory=list)
    host: str = "localhost"

    @property
    def short_name(self) -> str:
        return self.name.split("@")[-1] if "@" in self.name else self.name


@dataclass
class Bookmark:
    name: str
    dataset: str
    creation: str = ""
    host: str = "localhost"

    @property
    def short_name(self) -> str:
        return self.name.split("#")[-1] if "#" in self.name else self.name
