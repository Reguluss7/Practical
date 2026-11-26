from __future__ import annotations

from typing import Protocol, Sequence

from .domain import Reservation


class Notifier(Protocol):
    """Notification abstraction so channels can be swapped or faked in tests."""

    def send(self, reservation: Reservation) -> None: ...


class EmailSender:
    def __init__(self) -> None:
        self.sent_messages: list[str] = []

    def send(self, reservation: Reservation) -> None:
        msg = (
            f"[EMAIL -> {reservation.guest.email}] "
            f"Booking {reservation.booking_id} confirmed for Room {reservation.room.room_number} "
            f"({reservation.check_in} to {reservation.check_out}, ${reservation.total_price:.2f})."
        )
        self.sent_messages.append(msg)


class SmsSender:
    """Added in P04 Step 7 without modifying BookingService."""

    def __init__(self) -> None:
        self.sent_messages: list[str] = []

    def send(self, reservation: Reservation) -> None:
        target = reservation.guest.phone or reservation.guest.guest_id
        msg = (
            f"[SMS -> {target}] "
            f"Confirmed {reservation.booking_id}: Room {reservation.room.room_number} "
            f"{reservation.check_in}..{reservation.check_out}."
        )
        self.sent_messages.append(msg)


class CompositeNotifier:
    """Fan-out notifier to send Email + SMS together without touching BookingService."""

    def __init__(self, notifiers: Sequence[Notifier]) -> None:
        self._notifiers = list(notifiers)

    def send(self, reservation: Reservation) -> None:
        errors: list[Exception] = []
        for notifier in self._notifiers:
            try:
                notifier.send(reservation)
            except Exception as exc:
                errors.append(exc)
        if errors:
            raise RuntimeError(f"{len(errors)} notification channel(s) failed.") from errors[0]