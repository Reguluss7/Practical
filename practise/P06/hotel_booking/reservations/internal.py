from __future__ import annotations

from typing import Optional

from .domain import Reservation


class InMemoryReservationStore:
    def __init__(self) -> None:
        self._reservations: list[Reservation] = []

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