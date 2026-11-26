from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Optional


class RoomType(Enum):
    SINGLE = "SINGLE"
    DOUBLE = "DOUBLE"
    SUITE = "SUITE"


class BookingStatus(Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class Room:
    room_number: str
    room_type: RoomType
    nightly_rate: float

    def __post_init__(self) -> None:
        if self.nightly_rate <= 0:
            raise ValueError("Nightly rate must be positive.")


@dataclass(frozen=True)
class Guest:
    guest_id: str
    name: str
    email: str


@dataclass
class Booking:
    booking_id: str
    room: Room
    guest: Guest
    check_in: date
    check_out: date
    status: BookingStatus = BookingStatus.CONFIRMED

    def __post_init__(self) -> None:
        if self.check_out <= self.check_in:
            raise ValueError("check_out must be strictly after check_in.")

    @property
    def nights(self) -> int:
        return (self.check_out - self.check_in).days

    @property
    def total_price(self) -> float:
        return self.nights * self.room.nightly_rate

    def overlaps(self, check_in: date, check_out: date) -> bool:
        if self.status != BookingStatus.CONFIRMED:
            return False
        return self.check_in < check_out and check_in < self.check_out

    def cancel(self) -> None:
        if self.status == BookingStatus.CANCELLED:
            raise ValueError(f"Booking {self.booking_id} is already cancelled.")
        self.status = BookingStatus.CANCELLED


class Hotel:
    def __init__(self, name: str) -> None:
        self.name = name
        self._rooms: dict[str, Room] = {}
        self._bookings: dict[str, Booking] = {}
        self._next_booking_seq: int = 1

    # R1 — Room Inventory
    def add_room(self, room: Room) -> None:
        if room.room_number in self._rooms:
            raise ValueError(f"Room {room.room_number} already exists.")
        self._rooms[room.room_number] = room

    # R2 — Availability Search
    def find_available_rooms(
        self,
        check_in: date,
        check_out: date,
        room_type: Optional[RoomType] = None,
    ) -> list[Room]:
        self._validate_dates(check_in, check_out)
        available: list[Room] = []
        for room in self._rooms.values():
            if room_type is not None and room.room_type != room_type:
                continue
            if self._is_room_available(room.room_number, check_in, check_out):
                available.append(room)
        return available

    # R3 — Room Booking & Price Calculation
    def book_room(
        self,
        room_number: str,
        guest: Guest,
        check_in: date,
        check_out: date,
    ) -> Booking:
        self._validate_dates(check_in, check_out)
        if room_number not in self._rooms:
            raise ValueError(f"Room {room_number} does not exist.")
        if not self._is_room_available(room_number, check_in, check_out):
            raise ValueError(
                f"Room {room_number} is not available from {check_in} to {check_out}."
            )

        booking_id = f"BK-{self._next_booking_seq:04d}"
        self._next_booking_seq += 1

        booking = Booking(
            booking_id=booking_id,
            room=self._rooms[room_number],
            guest=guest,
            check_in=check_in,
            check_out=check_out,
        )
        self._bookings[booking_id] = booking
        return booking

    # R4 — Booking Cancellation
    def cancel_booking(self, booking_id: str) -> Booking:
        if booking_id not in self._bookings:
            raise ValueError(f"Booking {booking_id} not found.")
        booking = self._bookings[booking_id]
        booking.cancel()
        return booking

    # R5 — Guest Booking History
    def get_guest_bookings(self, guest_id: str) -> list[Booking]:
        return [
            booking
            for booking in self._bookings.values()
            if booking.guest.guest_id == guest_id
        ]

    def _is_room_available(
        self, room_number: str, check_in: date, check_out: date
    ) -> bool:
        return not any(
            b.room.room_number == room_number and b.overlaps(check_in, check_out)
            for b in self._bookings.values()
        )

    @staticmethod
    def _validate_dates(check_in: date, check_out: date) -> None:
        if check_out <= check_in:
            raise ValueError("check_out must be strictly after check_in.")


def run_proofs() -> None:
    hotel = Hotel("Grand Tashkent")

    # P1 (R1): Add rooms & reject duplicate
    hotel.add_room(Room("101", RoomType.SINGLE, 80.0))
    hotel.add_room(Room("201", RoomType.DOUBLE, 130.0))
    hotel.add_room(Room("301", RoomType.SUITE, 250.0))
    try:
        hotel.add_room(Room("101", RoomType.SINGLE, 80.0))
        raise AssertionError("Duplicate room should have failed.")
    except ValueError:
        pass

    g1 = Guest("G1", "Ali Karimov", "ali@example.com")
    g2 = Guest("G2", "Sara Malik", "sara@example.com")

    # P3 (R3): Standard booking & price check
    b1 = hotel.book_room("101", g1, date(2026, 12, 1), date(2026, 12, 4))
    assert b1.booking_id == "BK-0001"
    assert b1.nights == 3
    assert b1.total_price == 240.0
    assert b1.status == BookingStatus.CONFIRMED

    # P2 (R2): Availability excludes booked room 101
    avail = hotel.find_available_rooms(date(2026, 12, 1), date(2026, 12, 4))
    assert {r.room_number for r in avail} == {"201", "301"}

    # P3 (R3): Overlapping booking rejected
    try:
        hotel.book_room("101", g2, date(2026, 12, 3), date(2026, 12, 5))
        raise AssertionError("Overlapping booking should have failed.")
    except ValueError:
        pass

    # P3 (R3): Back-to-back booking allowed
    b2 = hotel.book_room("101", g2, date(2026, 12, 4), date(2026, 12, 6))
    assert b2.booking_id == "BK-0002"
    assert b2.total_price == 160.0

    # P4 (R4): Cancel frees room; double-cancel rejected
    hotel.cancel_booking(b1.booking_id)
    assert b1.status == BookingStatus.CANCELLED
    b3 = hotel.book_room("101", g2, date(2026, 12, 1), date(2026, 12, 4))
    assert b3.status == BookingStatus.CONFIRMED

    try:
        hotel.cancel_booking(b1.booking_id)
        raise AssertionError("Double cancellation should have failed.")
    except ValueError:
        pass

    # P5 (R5): Guest history preserves cancelled bookings
    g1_history = hotel.get_guest_bookings("G1")
    assert len(g1_history) == 1
    assert g1_history[0].booking_id == "BK-0001"
    assert g1_history[0].status == BookingStatus.CANCELLED

    print("All proof lines (P1–P5) passed.")


if __name__ == "__main__":
    run_proofs()