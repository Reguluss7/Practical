from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol


class RoomType(Enum):
    SINGLE = "SINGLE"
    DOUBLE = "DOUBLE"
    SUITE = "SUITE"


@dataclass(frozen=True)
class Room:
    room_number: str
    room_type: RoomType
    nightly_rate: float

    def __post_init__(self) -> None:
        if self.nightly_rate <= 0:
            raise ValueError("Nightly rate must be positive.")


class RoomCatalog(Protocol):
    def add_room(self, room: Room) -> None: ...
    def get_room(self, room_number: str) -> Optional[Room]: ...
    def list_rooms(self) -> list[Room]: ...