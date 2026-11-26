from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class Confirmation:
    booking_id: str
    guest_id: str
    guest_name: str
    guest_email: str
    guest_phone: str
    room_number: str
    check_in: date
    check_out: date
    total_price: float


class Notifier(Protocol):
    def send(self, confirmation: Confirmation) -> None: ...


__all__ = ["Confirmation", "Notifier"]