from __future__ import annotations

from typing import Optional

from .catalog import Room


class InMemoryRoomCatalog:
    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}

    def add_room(self, room: Room) -> None:
        if room.room_number in self._rooms:
            raise ValueError(f"Room {room.room_number} already exists.")
        self._rooms[room.room_number] = room

    def get_room(self, room_number: str) -> Optional[Room]:
        return self._rooms.get(room_number)

    def list_rooms(self) -> list[Room]:
        return list(self._rooms.values())