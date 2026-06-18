from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class PoolHealth(Enum):
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    FAULTED = "FAULTED"
    OFFLINE = "OFFLINE"
    UNAVAIL = "UNAVAIL"
    REMOVED = "REMOVED"
    SUSPENDED = "SUSPENDED"


class PoolStatus(Enum):
    ACTIVE = "ACTIVE"
    EXPORTED = "EXPORTED"
    DESTROYED = "DESTROYED"
    POTENTIALLY_ACTIVE = "POTENTIALLY_ACTIVE"


@dataclass
class Vdev:
    name: str
    type: str
    state: str
    read_errors: int = 0
    write_errors: int = 0
    checksum_errors: int = 0
    size: Optional[str] = None
    allocated: Optional[str] = None
    free: Optional[str] = None
    children: list["Vdev"] = field(default_factory=list)
    guid: Optional[int] = None
    path: Optional[str] = None
    ashift: Optional[int] = None


@dataclass
class Pool:
    name: str
    health: PoolHealth = PoolHealth.ONLINE
    size: str = "0"
    allocated: str = "0"
    free: str = "0"
    fragmentation: str = "-"
    capacity: str = "0"
    dedup_ratio: str = "1.00x"
    status: PoolStatus = PoolStatus.ACTIVE
    altroot: Optional[str] = None
    vdevs: list[Vdev] = field(default_factory=list)
    properties: dict[str, str] = field(default_factory=dict)
    scan: Optional[str] = None
    errors: Optional[str] = None
    host: str = "localhost"

    @property
    def health_color(self) -> str:
        return {
            PoolHealth.ONLINE: "green",
            PoolHealth.DEGRADED: "yellow",
            PoolHealth.FAULTED: "red",
            PoolHealth.OFFLINE: "gray",
            PoolHealth.UNAVAIL: "red",
            PoolHealth.REMOVED: "gray",
            PoolHealth.SUSPENDED: "magenta",
        }.get(self.health, "white")

    @property
    def used_percent(self) -> float:
        try:
            return float(self.capacity.strip("%"))
        except (ValueError, AttributeError):
            return 0.0
