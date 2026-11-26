from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from hotel_booking.api import create_app
from hotel_booking.notifications.internal import EmailSender
from hotel_booking.payments.internal import SimulatedPaymentGateway
from hotel_booking.reservations import BookingService
from hotel_booking.reservations.internal import InMemoryReservationStore
from hotel_booking.rooms import Room, RoomType
from hotel_booking.rooms.internal import InMemoryRoomCatalog


class TestHotelBookingApi(unittest.TestCase):
    def setUp(self) -> None:
        rooms = InMemoryRoomCatalog()
        rooms.add_room(Room("R7", RoomType.DOUBLE, 120.0))
        rooms.add_room(Room("R8", RoomType.SUITE, 200.0))
        rooms.add_room(Room("R9", RoomType.SINGLE, 80.0))
        service = BookingService(
            rooms=rooms,
            store=InMemoryReservationStore(),
            notifier=EmailSender(),
            payments=SimulatedPaymentGateway(),
        )
        self.client = TestClient(create_app(service))

    # 1. Search returns 200 with limit & after pagination
    def test_search_available_rooms_returns_200(self) -> None:
        res = self.client.get(
            "/rooms/available",
            params={"check_in": "2026-12-01", "check_out": "2026-12-04", "limit": 2},
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()
        self.assertEqual([r["room_number"] for r in body["rooms"]], ["R7", "R8"])
        self.assertEqual(body["next_after"], "R8")

        page2 = self.client.get(
            "/rooms/available",
            params={
                "check_in": "2026-12-01",
                "check_out": "2026-12-04",
                "limit": 2,
                "after": body["next_after"],
            },
        )
        self.assertEqual(page2.status_code, 200)
        self.assertEqual([r["room_number"] for r in page2.json()["rooms"]], ["R9"])
        self.assertIsNone(page2.json()["next_after"])

    # 2. Book returns 201, overlapping clash returns 409
    def test_book_returns_201_then_clash_returns_409(self) -> None:
        maya = {
            "room_number": "R7",
            "guest_id": "G-MAYA",
            "guest_name": "Maya",
            "guest_email": "maya@example.com",
            "check_in": "2026-12-01",
            "check_out": "2026-12-04",
        }
        r1 = self.client.post("/reservations", json=maya)
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r1.json()["booking_id"], "BK-0001")
        self.assertEqual(r1.json()["total_price"], 360.0)

        omar = {
            "room_number": "R7",
            "guest_id": "G-OMAR",
            "guest_name": "Omar",
            "guest_email": "omar@example.com",
            "check_in": "2026-12-02",
            "check_out": "2026-12-05",
        }
        r2 = self.client.post("/reservations", json=omar)
        self.assertEqual(r2.status_code, 409)

    # 3. Wrong dates return 400
    def test_wrong_dates_return_400(self) -> None:
        search_res = self.client.get(
            "/rooms/available",
            params={"check_in": "2026-12-05", "check_out": "2026-12-05"},
        )
        self.assertEqual(search_res.status_code, 400)

        book_res = self.client.post(
            "/reservations",
            json={
                "room_number": "R7",
                "guest_id": "G-MAYA",
                "guest_name": "Maya",
                "guest_email": "maya@example.com",
                "check_in": "2026-12-05",
                "check_out": "2026-12-01",
            },
        )
        self.assertEqual(book_res.status_code, 400)

    # 4. Cancel returns 204, second cancel returns 404
    def test_cancel_returns_204_then_404(self) -> None:
        created = self.client.post(
            "/reservations",
            json={
                "room_number": "R8",
                "guest_id": "G-OMAR",
                "guest_name": "Omar",
                "guest_email": "omar@example.com",
                "check_in": "2026-12-01",
                "check_out": "2026-12-03",
            },
        )
        booking_id = created.json()["booking_id"]

        first_cancel = self.client.delete(f"/reservations/{booking_id}")
        self.assertEqual(first_cancel.status_code, 204)

        second_cancel = self.client.delete(f"/reservations/{booking_id}")
        self.assertEqual(second_cancel.status_code, 404)


if __name__ == "__main__":
    unittest.main()