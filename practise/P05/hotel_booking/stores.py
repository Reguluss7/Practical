from __future__ import annotations

from typing import Optional, Protocol

from .domain import Reservation, Room


class ReservationStore(Protocol):
    """Storage abstraction so BookingService never depends on a list or database."""

    def add_room(self, room: Room) -> None: ...
    def get_room(self, room_number: str) -> Optional[Room]: ...
    def list_rooms(self) -> list[Room]: ...
    def save_reservation(self, reservation: Reservation) -> None: ...
    def get_reservation(self, booking_id: str) -> Optional[Reservation]: ...
    def list_reservations(self) -> list[Reservation]: ...


class InMemoryReservationStore:
    """List/dict-backed store used today; swappable for PostgreSQL in P07."""

    def __init__(self) -> None:
        self._rooms: dict[str, Room] = {}
        self._reservations: list[Reservation] = []

    def add_room(self, room: Room) -> None:
        if room.room_number in self._rooms:
            raise ValueError(f"Room {room.room_number} already exists.")
        self._rooms[room.room_number] = room

    def get_room(self, room_number: str) -> Optional[Room]:
        return self._rooms.get(room_number)

    def list_rooms(self) -> list[Room]:
        return list(self._rooms.values())

    def save_reservation(self, reservation: Reservation) -> None:
        for i, existing in enumerate(self._reservations):
            if existing.booking_id == reservation.booking_id:
                self._reservations[i] = reservation
                return
        self._reservations.append(reservation)

    def get_reservation(self, booking_id: str) -> Optional[Reservation]:
        for reservation in self._reservations:
            if reservation.booking_id == booking_id:
                return reservation
        return None

    def list_reservations(self) -> list[Reservation]:
        return list(self._reservations)