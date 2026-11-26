from __future__ import annotations

from datetime import date
from typing import Optional, Protocol

from hotel_booking.notifications import Confirmation, Notifier
from hotel_booking.payments import PaymentGateway, PaymentRequest
from hotel_booking.rooms import Room, RoomCatalog, RoomType

from .domain import Guest, Reservation


class ReservationStore(Protocol):
    def save_reservation(self, reservation: Reservation) -> None: ...
    def get_reservation(self, booking_id: str) -> Optional[Reservation]: ...
    def list_reservations(self) -> list[Reservation]: ...


class BookingService:
    """Depends only on public contracts across Rooms, Payments, and Notifications."""

    def __init__(
        self,
        rooms: RoomCatalog,
        store: ReservationStore,
        notifier: Notifier,
        payments: PaymentGateway,
    ) -> None:
        self._rooms = rooms
        self._store = store
        self._notifier = notifier
        self._payments = payments
        self._next_seq = 1

    # R1 — Room Inventory (delegated to Rooms)
    def add_room(self, room: Room) -> None:
        self._rooms.add_room(room)

    # R2 — Availability Search
    def find_available_rooms(
        self,
        check_in: date,
        check_out: date,
        room_type: Optional[RoomType] = None,
    ) -> list[Room]:
        self._validate_dates(check_in, check_out)
        available: list[Room] = []
        for room in self._rooms.list_rooms():
            if room_type is not None and room.room_type != room_type:
                continue
            if self._is_room_available(room.room_number, check_in, check_out):
                available.append(room)
        return available

    # R3 — Room Booking & R6 — Resilient Notification
    def reserve(
        self,
        room_number: str,
        guest: Guest,
        check_in: date,
        check_out: date,
    ) -> Reservation:
        self._validate_dates(check_in, check_out)
        room = self._rooms.get_room(room_number)
        if room is None:
            raise ValueError(f"Room {room_number} does not exist.")
        if not self._is_room_available(room_number, check_in, check_out):
            raise ValueError(
                f"Room {room_number} is not available from {check_in} to {check_out}."
            )

        booking_id = f"BK-{self._next_seq:04d}"
        self._next_seq += 1

        reservation = Reservation(
            booking_id=booking_id,
            room=room,
            guest=guest,
            check_in=check_in,
            check_out=check_out,
        )

        payment = self._payments.charge_deposit(
            PaymentRequest(
                booking_id=booking_id,
                guest_id=guest.guest_id,
                total_price=reservation.total_price,
            )
        )
        reservation.deposit_paid = payment.deposit_amount

        self._store.save_reservation(reservation)

        confirmation = Confirmation(
            booking_id=reservation.booking_id,
            guest_id=guest.guest_id,
            guest_name=guest.name,
            guest_email=guest.email,
            guest_phone=guest.phone,
            room_number=room.room_number,
            check_in=check_in,
            check_out=check_out,
            total_price=reservation.total_price,
        )
        try:
            self._notifier.send(confirmation)
        except Exception:
            reservation.notification_sent = False

        return reservation

    # R4 — Booking Cancellation
    def cancel(self, booking_id: str) -> Reservation:
        reservation = self._store.get_reservation(booking_id)
        if reservation is None:
            raise ValueError(f"Booking {booking_id} not found.")
        reservation.cancel()
        self._store.save_reservation(reservation)
        return reservation

    # R5 — Guest Booking History
    def get_guest_bookings(self, guest_id: str) -> list[Reservation]:
        return [
            r
            for r in self._store.list_reservations()
            if r.guest.guest_id == guest_id
        ]

    def _is_room_available(
        self, room_number: str, check_in: date, check_out: date
    ) -> bool:
        return not any(
            r.room.room_number == room_number and r.overlaps(check_in, check_out)
            for r in self._store.list_reservations()
        )

    @staticmethod
    def _validate_dates(check_in: date, check_out: date) -> None:
        if check_out <= check_in:
            raise ValueError("check_out must be strictly after check_in.")