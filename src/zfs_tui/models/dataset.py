from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class DatasetType(Enum):
    FILESYSTEM = "filesystem"
    VOLUME = "volume"
    SNAPSHOT = "snapshot"
    BOOKMARK = "bookmark"


@dataclass
class DatasetProperties:
    used: str = "0"
    available: str = "0"
    referenced: str = "0"
    compressratio: str = "1.00x"
    compression: str = "off"
    mountpoint: str = "/"
    quota: str = "none"
    reservation: str = "none"
    recordsize: str = "128K"
    atime: str = "on"
    relatime: str = "off"
    encryption: str = "off"
    checksum: str = "on"
    dedup: str = "off"
    copies: str = "1"
    refquota: str = "none"
    refreservation: str = "none"
    logicalused: str = "0"
    logicalreferenced: str = "0"


@dataclass
class Dataset:
    name: str
    pool: str
    type: DatasetType = DatasetType.FILESYSTEM
    properties: DatasetProperties = field(default_factory=DatasetProperties)
    children: list["Dataset"] = field(default_factory=list)
    origin: Optional[str] = None
    creation: Optional[str] = None
    parent: Optional[str] = None
    host: str = "localhost"

    @property
    def short_name(self) -> str:
        return self.name.split("/")[-1] if "/" in self.name else self.name

    @property
    def depth(self) -> int:
        return len(self.name.split("/")) - 1
