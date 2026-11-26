from __future__ import annotations

from typing import Optional

import psycopg

from .catalog import Room, RoomType


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


class PostgresRoomCatalog:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def add_room(self, room: Room) -> None:
        try:
            with psycopg.connect(self._dsn) as conn:
                conn.execute(
                    "INSERT INTO rooms (room_number, room_type, nightly_rate) VALUES (%s, %s, %s)",
                    (room.room_number, room.room_type.value, room.nightly_rate),
                )
        except psycopg.errors.UniqueViolation as exc:
            raise ValueError(f"Room {room.room_number} already exists.") from exc

    def get_room(self, room_number: str) -> Optional[Room]:
        with psycopg.connect(self._dsn) as conn:
            row = conn.execute(
                "SELECT room_number, room_type, nightly_rate FROM rooms WHERE room_number = %s",
                (room_number,),
            ).fetchone()
        if row is None:
            return None
        return Room(
            room_number=row[0],
            room_type=RoomType(row[1]),
            nightly_rate=float(row[2]),
        )

    def list_rooms(self) -> list[Room]:
        with psycopg.connect(self._dsn) as conn:
            rows = conn.execute(
                "SELECT room_number, room_type, nightly_rate FROM rooms ORDER BY room_number"
            ).fetchall()
        return [
            Room(
                room_number=row[0],
                room_type=RoomType(row[1]),
                nightly_rate=float(row[2]),
            )
            for row in rows
        ]