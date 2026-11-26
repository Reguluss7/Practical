from __future__ import annotations

from typing import Optional

import psycopg

from hotel_booking.rooms import Room, RoomType

from .domain import BookingStatus, Guest, Reservation


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


class PostgresReservationStore:
    def __init__(self, dsn: str) -> None:
        self._dsn = dsn

    def save_reservation(self, reservation: Reservation) -> None:
        with psycopg.connect(self._dsn) as conn:
            conn.execute(
                """
                INSERT INTO reservations (
                    booking_id, room_number, guest_id, guest_name, guest_email,
                    guest_phone, check_in, check_out, status, notification_sent, deposit_paid
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (booking_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    notification_sent = EXCLUDED.notification_sent,
                    deposit_paid = EXCLUDED.deposit_paid
                """,
                (
                    reservation.booking_id,
                    reservation.room.room_number,
                    reservation.guest.guest_id,
                    reservation.guest.name,
                    reservation.guest.email,
                    reservation.guest.phone,
                    reservation.check_in,
                    reservation.check_out,
                    reservation.status.value,
                    reservation.notification_sent,
                    reservation.deposit_paid,
                ),
            )

    def get_reservation(self, booking_id: str) -> Optional[Reservation]:
        with psycopg.connect(self._dsn) as conn:
            row = conn.execute(
                """
                SELECT r.booking_id, rm.room_number, rm.room_type, rm.nightly_rate,
                       r.guest_id, r.guest_name, r.guest_email, r.guest_phone,
                       r.check_in, r.check_out, r.status, r.notification_sent, r.deposit_paid
                FROM reservations r
                JOIN rooms rm ON rm.room_number = r.room_number
                WHERE r.booking_id = %s
                """,
                (booking_id,),
            ).fetchone()
        return self._row_to_reservation(row) if row is not None else None

    def list_reservations(self) -> list[Reservation]:
        with psycopg.connect(self._dsn) as conn:
            rows = conn.execute(
                """
                SELECT r.booking_id, rm.room_number, rm.room_type, rm.nightly_rate,
                       r.guest_id, r.guest_name, r.guest_email, r.guest_phone,
                       r.check_in, r.check_out, r.status, r.notification_sent, r.deposit_paid
                FROM reservations r
                JOIN rooms rm ON rm.room_number = r.room_number
                ORDER BY r.booking_id
                """
            ).fetchall()
        return [self._row_to_reservation(row) for row in rows]

    @staticmethod
    def _row_to_reservation(row: tuple) -> Reservation:
        return Reservation(
            booking_id=row[0],
            room=Room(
                room_number=row[1],
                room_type=RoomType(row[2]),
                nightly_rate=float(row[3]),
            ),
            guest=Guest(
                guest_id=row[4],
                name=row[5],
                email=row[6],
                phone=row[7],
            ),
            check_in=row[8],
            check_out=row[9],
            status=BookingStatus(row[10]),
            notification_sent=bool(row[11]),
            deposit_paid=float(row[12]),
        )