from __future__ import annotations

import threading
import time
from datetime import date

from hotel_booking import (
    BookingService,
    CompositeNotifier,
    EmailSender,
    Guest,
    InMemoryReservationStore,
    Room,
    RoomType,
    SmsSender,
)


def run_demo() -> None:
    store = InMemoryReservationStore()
    email = EmailSender()
    sms = SmsSender()
    service = BookingService(store=store, notifier=CompositeNotifier([email, sms]))

    service.add_room(Room("101", RoomType.SINGLE, 80.0))
    service.add_room(Room("201", RoomType.DOUBLE, 130.0))

    ali = Guest("G1", "Ali Karimov", "ali@example.com", "+998901234567")
    sara = Guest("G2", "Sara Malik", "sara@example.com", "+998907654321")

    free = service.find_available_rooms(date(2026, 12, 1), date(2026, 12, 4))
    print("Available rooms:", [r.room_number for r in free])

    b1 = service.reserve("101", ali, date(2026, 12, 1), date(2026, 12, 4))
    print(f"Booked {b1.booking_id}: Room {b1.room.room_number}, ${b1.total_price:.2f}")
    print("Notifications sent:", email.sent_messages[-1], "|", sms.sent_messages[-1])

    try:
        service.reserve("101", sara, date(2026, 12, 2), date(2026, 12, 5))
    except ValueError as err:
        print("Clash refused:", err)

    service.cancel(b1.booking_id)
    print(f"Cancelled {b1.booking_id}. Room 101 free again:",
          [r.room_number for r in service.find_available_rooms(date(2026, 12, 1), date(2026, 12, 4))])


def run_race_demo() -> None:
    """Demonstrates the unguarded check-then-act race (preserved from P03; fixed in P07)."""
    store = InMemoryReservationStore()
    service = BookingService(store=store, notifier=EmailSender())
    service.add_room(Room("301", RoomType.SUITE, 250.0))

    orig_check = service._is_room_available

    def slow_check(room_number: str, check_in: date, check_out: date) -> bool:
        available = orig_check(room_number, check_in, check_out)
        time.sleep(0.05)  # widen race window between check and save
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


if __name__ == "__main__":
    run_demo()
    run_race_demo()