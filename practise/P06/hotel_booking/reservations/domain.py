from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from hotel_booking.rooms import Room


class BookingStatus(Enum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class Guest:
    guest_id: str
    name: str
    email: str
    phone: str = ""


@dataclass
class Reservation:
    booking_id: str
    room: Room
    guest: Guest
    check_in: date
    check_out: date
    status: BookingStatus = BookingStatus.CONFIRMED
    notification_sent: bool = True
    deposit_paid: float = 0.0

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