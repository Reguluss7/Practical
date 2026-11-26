from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from hotel_booking.api import QueryCounter, create_app
from hotel_booking.api_cache import InMemoryAvailabilityCache
from hotel_booking.notifications.internal import EmailSender
from hotel_booking.payments.internal import SimulatedPaymentGateway
from hotel_booking.reservations import BookingService
from hotel_booking.reservations.internal import InMemoryReservationStore
from hotel_booking.rooms import Room, RoomType
from hotel_booking.rooms.internal import InMemoryRoomCatalog
from main import CountingReservationStore, CountingRoomCatalog


class TestHotelBookingApi(unittest.TestCase):
    def setUp(self) -> None:
        self.counter = QueryCounter()
        raw_rooms = InMemoryRoomCatalog()
        raw_rooms.add_room(Room("R7", RoomType.DOUBLE, 120.0))
        raw_rooms.add_room(Room("R8", RoomType.SUITE, 200.0))
        raw_rooms.add_room(Room("R9", RoomType.SINGLE, 80.0))

        self.cache = InMemoryAvailabilityCache(ttl_seconds=30)
        service = BookingService(
            rooms=CountingRoomCatalog(raw_rooms, self.counter),
            store=CountingReservationStore(InMemoryReservationStore(), self.counter),
            notifier=EmailSender(),
            payments=SimulatedPaymentGateway(),
        )
        self.counter.db_queries = 0
        self.client = TestClient(create_app(service, cache=self.cache, counter=self.counter))

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

    # 5. P08 — Repeat search hits cache without extra DB queries
    def test_repeat_search_hits_cache_and_skips_db(self) -> None:
        self.client.get("/rooms/available", params={"check_in": "2026-11-12", "check_out": "2026-11-14"})
        self.client.get("/rooms/available", params={"check_in": "2026-11-12", "check_out": "2026-11-14"})

        stats = self.client.get("/stats").json()
        self.assertEqual(stats["cache_misses"], 1)
        self.assertEqual(stats["cache_hits"], 1)
        self.assertEqual(stats["db_queries"], 2)  # list_rooms + list_reservations once

    # 6. P08 — POST reserve and DELETE cancel invalidate the cache version
    def test_reserve_and_cancel_invalidate_cache(self) -> None:
        params = {"check_in": "2026-12-01", "check_out": "2026-12-04"}
        first = self.client.get("/rooms/available", params=params).json()
        self.assertIn("R7", [r["room_number"] for r in first["rooms"]])
        v1 = self.client.get("/stats").json()["cache_version"]

        created = self.client.post(
            "/reservations",
            json={
                "room_number": "R7",
                "guest_id": "G-MAYA",
                "guest_name": "Maya",
                "guest_email": "maya@example.com",
                "check_in": "2026-12-01",
                "check_out": "2026-12-04",
            },
        )
        self.assertEqual(created.status_code, 201)
        booking_id = created.json()["booking_id"]
        v2 = self.client.get("/stats").json()["cache_version"]
        self.assertEqual(v2, v1 + 1)

        after_book = self.client.get("/rooms/available", params=params).json()
        self.assertNotIn("R7", [r["room_number"] for r in after_book["rooms"]])

        self.client.delete(f"/reservations/{booking_id}")
        v3 = self.client.get("/stats").json()["cache_version"]
        self.assertEqual(v3, v2 + 1)

        after_cancel = self.client.get("/rooms/available", params=params).json()
        self.assertIn("R7", [r["room_number"] for r in after_cancel["rooms"]])


if __name__ == "__main__":
    unittest.main()