from __future__ import annotations

import unittest
from datetime import date

from hotel_booking.notifications import Confirmation
from hotel_booking.notifications.internal import CompositeNotifier, EmailSender, SmsSender
from hotel_booking.payments.internal import SimulatedPaymentGateway
from hotel_booking.reservations import BookingService, BookingStatus, Guest
from hotel_booking.reservations.internal import InMemoryReservationStore
from hotel_booking.rooms import Room, RoomType
from hotel_booking.rooms.internal import InMemoryRoomCatalog


class FailingNotifier:
    """Test double that simulates an SMTP/SMS outage."""

    def send(self, confirmation: Confirmation) -> None:
        raise RuntimeError("SMTP server unreachable")


class TestBookingService(unittest.TestCase):
    def setUp(self) -> None:
        self.rooms = InMemoryRoomCatalog()
        self.store = InMemoryReservationStore()
        self.payments = SimulatedPaymentGateway()
        self.email = EmailSender()
        self.service = BookingService(
            rooms=self.rooms,
            store=self.store,
            notifier=self.email,
            payments=self.payments,
        )
        self.service.add_room(Room("101", RoomType.SINGLE, 80.0))
        self.service.add_room(Room("201", RoomType.DOUBLE, 130.0))
        self.g1 = Guest("G1", "Ali Karimov", "ali@example.com", "+998901234567")
        self.g2 = Guest("G2", "Sara Malik", "sara@example.com", "+998907654321")

    # 1. R2 — Search excludes booked rooms
    def test_search_returns_only_free_rooms(self) -> None:
        self.service.reserve("101", self.g1, date(2026, 12, 1), date(2026, 12, 4))
        free = self.service.find_available_rooms(date(2026, 12, 1), date(2026, 12, 4))
        self.assertEqual([r.room_number for r in free], ["201"])

    # 2. R3 — Reserve calculates price and sends confirmation
    def test_reserve_succeeds_and_calculates_price(self) -> None:
        booking = self.service.reserve("101", self.g1, date(2026, 12, 1), date(2026, 12, 4))
        self.assertEqual(booking.booking_id, "BK-0001")
        self.assertEqual(booking.nights, 3)
        self.assertEqual(booking.total_price, 240.0)
        self.assertEqual(booking.status, BookingStatus.CONFIRMED)
        self.assertEqual(len(self.email.sent_messages), 1)

    # 3. R3 — Overlapping booking refused
    def test_reserve_refuses_overlapping_dates(self) -> None:
        self.service.reserve("101", self.g1, date(2026, 12, 1), date(2026, 12, 4))
        with self.assertRaises(ValueError):
            self.service.reserve("101", self.g2, date(2026, 12, 3), date(2026, 12, 5))

    # 4. R2/R3 — Back-to-back booking allowed
    def test_reserve_allows_back_to_back_dates(self) -> None:
        self.service.reserve("101", self.g1, date(2026, 12, 1), date(2026, 12, 4))
        b2 = self.service.reserve("101", self.g2, date(2026, 12, 4), date(2026, 12, 6))
        self.assertEqual(b2.status, BookingStatus.CONFIRMED)
        self.assertEqual(b2.total_price, 160.0)

    # 5. R4 — Cancel frees room for rebooking
    def test_cancel_frees_room_for_rebooking(self) -> None:
        b1 = self.service.reserve("101", self.g1, date(2026, 12, 1), date(2026, 12, 4))
        self.service.cancel(b1.booking_id)
        self.assertEqual(b1.status, BookingStatus.CANCELLED)

        b2 = self.service.reserve("101", self.g2, date(2026, 12, 1), date(2026, 12, 4))
        self.assertEqual(b2.status, BookingStatus.CONFIRMED)

    # 6. R4/R5 — Double cancel rejected & guest history preserved
    def test_double_cancel_rejected_and_history_kept(self) -> None:
        b1 = self.service.reserve("101", self.g1, date(2026, 12, 1), date(2026, 12, 4))
        self.service.cancel(b1.booking_id)
        with self.assertRaises(ValueError):
            self.service.cancel(b1.booking_id)

        history = self.service.get_guest_bookings("G1")
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].status, BookingStatus.CANCELLED)

    # 7. R6 — Failed notification never loses a booking
    def test_failed_notification_never_loses_booking(self) -> None:
        service = BookingService(
            rooms=self.rooms,
            store=self.store,
            notifier=FailingNotifier(),
            payments=self.payments,
        )
        booking = service.reserve("101", self.g1, date(2026, 12, 1), date(2026, 12, 4))

        self.assertEqual(booking.status, BookingStatus.CONFIRMED)
        self.assertFalse(booking.notification_sent)
        saved = self.store.get_reservation(booking.booking_id)
        self.assertIsNotNone(saved)
        self.assertEqual(saved.booking_id, booking.booking_id)

    # 8. Open/Closed — Add SMS without touching BookingService
    def test_sms_and_email_work_without_changing_booking_service(self) -> None:
        sms = SmsSender()
        multi = CompositeNotifier([self.email, sms])
        service = BookingService(
            rooms=self.rooms,
            store=self.store,
            notifier=multi,
            payments=self.payments,
        )

        service.reserve("201", self.g1, date(2026, 12, 5), date(2026, 12, 7))

        self.assertEqual(len(self.email.sent_messages), 1)
        self.assertEqual(len(sms.sent_messages), 1)
        self.assertIn("+998901234567", sms.sent_messages[0])


if __name__ == "__main__":
    unittest.main()