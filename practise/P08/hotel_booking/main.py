from __future__ import annotations

import argparse
import os
import threading
import time
from datetime import date
from typing import Optional

import uvicorn

from hotel_booking.api import QueryCounter, create_app
from hotel_booking.api_cache import (
    AvailabilityCache,
    NoOpAvailabilityCache,
    RedisAvailabilityCache,
)
from hotel_booking.notifications.internal import CompositeNotifier, EmailSender, SmsSender
from hotel_booking.payments.internal import SimulatedPaymentGateway
from hotel_booking.reservations import BookingService, Guest, Reservation, ReservationStore
from hotel_booking.reservations.internal import (
    InMemoryReservationStore,
    PostgresReservationStore,
)
from hotel_booking.rooms import Room, RoomCatalog, RoomType
from hotel_booking.rooms.internal import InMemoryRoomCatalog, PostgresRoomCatalog

DEFAULT_DSN = "postgresql://hotel:hotel@localhost:5433/hotel_booking"
DEFAULT_REDIS_URL = "redis://localhost:6379/0"


class CountingRoomCatalog:
    def __init__(self, inner: RoomCatalog, counter: QueryCounter) -> None:
        self._inner = inner
        self._counter = counter

    def add_room(self, room: Room) -> None:
        self._counter.increment()
        self._inner.add_room(room)

    def get_room(self, room_number: str) -> Optional[Room]:
        self._counter.increment()
        return self._inner.get_room(room_number)

    def list_rooms(self) -> list[Room]:
        self._counter.increment()
        return self._inner.list_rooms()


class CountingReservationStore:
    def __init__(self, inner: ReservationStore, counter: QueryCounter) -> None:
        self._inner = inner
        self._counter = counter

    def save_reservation(self, reservation: Reservation) -> None:
        self._counter.increment()
        self._inner.save_reservation(reservation)

    def get_reservation(self, booking_id: str) -> Optional[Reservation]:
        self._counter.increment()
        return self._inner.get_reservation(booking_id)

    def list_reservations(self) -> list[Reservation]:
        self._counter.increment()
        return self._inner.list_reservations()


def build_postgres_service(counter: QueryCounter) -> BookingService:
    dsn = os.getenv("DATABASE_URL", DEFAULT_DSN)
    rooms = CountingRoomCatalog(PostgresRoomCatalog(dsn), counter)
    store = CountingReservationStore(PostgresReservationStore(dsn), counter)
    notifier = CompositeNotifier([EmailSender(), SmsSender()])
    payments = SimulatedPaymentGateway()
    service = BookingService(rooms=rooms, store=store, notifier=notifier, payments=payments)
    # Reset startup initialization query so /stats starts at 0
    counter.db_queries = 0
    return service


def run_demo() -> None:
    rooms = InMemoryRoomCatalog()
    store = InMemoryReservationStore()
    payments = SimulatedPaymentGateway()
    email = EmailSender()
    sms = SmsSender()
    service = BookingService(
        rooms=rooms,
        store=store,
        notifier=CompositeNotifier([email, sms]),
        payments=payments,
    )

    service.add_room(Room("101", RoomType.SINGLE, 80.0))
    service.add_room(Room("201", RoomType.DOUBLE, 130.0))

    ali = Guest("G1", "Ali Karimov", "ali@example.com", "+998901234567")
    sara = Guest("G2", "Sara Malik", "sara@example.com", "+998907654321")

    free = service.find_available_rooms(date(2026, 12, 1), date(2026, 12, 4))
    print("Available rooms:", [r.room_number for r in free])

    b1 = service.reserve("101", ali, date(2026, 12, 1), date(2026, 12, 4))
    print(
        f"Booked {b1.booking_id}: Room {b1.room.room_number}, "
        f"${b1.total_price:.2f} (deposit ${b1.deposit_paid:.2f})"
    )
    print("Notifications sent:", email.sent_messages[-1], "|", sms.sent_messages[-1])

    try:
        service.reserve("101", sara, date(2026, 12, 2), date(2026, 12, 5))
    except ValueError as err:
        print("Clash refused:", err)

    service.cancel(b1.booking_id)
    print(
        f"Cancelled {b1.booking_id}. Room 101 free again:",
        [r.room_number for r in service.find_available_rooms(date(2026, 12, 1), date(2026, 12, 4))],
    )


def run_race_demo() -> None:
    rooms = InMemoryRoomCatalog()
    store = InMemoryReservationStore()
    service = BookingService(
        rooms=rooms,
        store=store,
        notifier=EmailSender(),
        payments=SimulatedPaymentGateway(),
    )
    service.add_room(Room("301", RoomType.SUITE, 250.0))

    orig_check = service._is_room_available

    def slow_check(room_number: str, check_in: date, check_out: date) -> bool:
        available = orig_check(room_number, check_in, check_out)
        time.sleep(0.05)
        return available

    service._is_room_available = slow_check  # type: ignore[method-assign]

    results: list[str] = []
    barrier = threading.Barrier(2)

    def attempt(guest: Guest) -> None:
        barrier.wait()
        try:
            res = service.reserve("301", guest, date(2026, 12, 10), date(2026, 12, 12))
            results.append(f"{guest.name} booked {res.booking_id}")
        except ValueError as err:
            results.append(f"{guest.name} failed: {err}")

    t1 = threading.Thread(target=attempt, args=(Guest("G1", "Ali", "a@x.com"),))
    t2 = threading.Thread(target=attempt, args=(Guest("G2", "Sara", "s@x.com"),))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    print("\nRace demo results (2 threads, same room & dates):")
    for line in results:
        print(" ", line)
    print("Confirmed bookings stored for Room 301:", len(store.list_reservations()))


def main() -> None:
    parser = argparse.ArgumentParser(description="Hotel Booking App")
    parser.add_argument("--demo", action="store_true", help="Run the P06 console demo")
    parser.add_argument("--race", action="store_true", help="Run the P06 concurrency race demo")
    parser.add_argument("--no-cache", action="store_true", help="Disable Redis cache (Step 1 baseline)")
    parser.add_argument("--no-invalidate", action="store_true", help="Skip cache invalidation (Step 5 stale demo)")
    args = parser.parse_args()

    if args.demo:
        run_demo()
        return
    if args.race:
        run_race_demo()
        return

    counter = QueryCounter()
    service = build_postgres_service(counter)
    redis_url = os.getenv("REDIS_URL", DEFAULT_REDIS_URL)
    cache: AvailabilityCache = (
        NoOpAvailabilityCache() if args.no_cache else RedisAvailabilityCache(redis_url, ttl_seconds=30)
    )
    app = create_app(
        service=service,
        cache=cache,
        counter=counter,
        invalidate_on_write=not args.no_invalidate,
    )
    uvicorn.run(app, host="127.0.0.1", port=5080)


if __name__ == "__main__":
    main()