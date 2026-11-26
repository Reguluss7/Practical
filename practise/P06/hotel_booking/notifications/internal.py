from __future__ import annotations

from typing import Sequence

from . import Confirmation, Notifier


class EmailSender:
    def __init__(self) -> None:
        self.sent_messages: list[str] = []

    def send(self, confirmation: Confirmation) -> None:
        msg = (
            f"[EMAIL -> {confirmation.guest_email}] "
            f"Booking {confirmation.booking_id} confirmed for Room {confirmation.room_number} "
            f"({confirmation.check_in} to {confirmation.check_out}, ${confirmation.total_price:.2f})."
        )
        self.sent_messages.append(msg)


class SmsSender:
    def __init__(self) -> None:
        self.sent_messages: list[str] = []

    def send(self, confirmation: Confirmation) -> None:
        target = confirmation.guest_phone or confirmation.guest_id
        msg = (
            f"[SMS -> {target}] "
            f"Confirmed {confirmation.booking_id}: Room {confirmation.room_number} "
            f"{confirmation.check_in}..{confirmation.check_out}."
        )
        self.sent_messages.append(msg)


class CompositeNotifier:
    def __init__(self, notifiers: Sequence[Notifier]) -> None:
        self._notifiers = list(notifiers)

    def send(self, confirmation: Confirmation) -> None:
        errors: list[Exception] = []
        for notifier in self._notifiers:
            try:
                notifier.send(confirmation)
            except Exception as exc:
                errors.append(exc)
        if errors:
            raise RuntimeError(f"{len(errors)} notification channel(s) failed.") from errors[0]