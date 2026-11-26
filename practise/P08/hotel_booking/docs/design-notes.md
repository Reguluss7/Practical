# Design Notes

## 1. Domain Model & Responsibilities
- **`Room`**: Immutable value/entity holding `room_number`, `room_type`, and `nightly_rate`. Validates that `nightly_rate > 0`.
- **`Guest`**: Identifies the person making a reservation (`guest_id`, `name`, `email`).
- **`Booking`**: Owns date-range math (`nights`, `total_price`), overlap detection (`overlaps()`), and status transitions (`cancel()`).
- **`Hotel`**: Aggregate root coordinating rooms and bookings. Enforces invariants (unique room numbers, no overlapping confirmed bookings, ID generation).

## 2. Date Overlap Rule
Dates are treated as half-open intervals `[check_in, check_out)`. Two intervals overlap if and only if:
```text
a.check_in < b.check_out and b.check_in < a.check_out

---

# P04 — Refactoring & SOLID Design Notes

## Step 1 · What Refactoring Is
Refactoring restructures internal code to make it easier to understand and change **without altering observable behaviour**.
- **Must stay the same:** All R1–R5 rules, price calculation, clash rejection, cancellation semantics, guest history, and the concurrency race behaviour.
- **Changes:** File layout, dependency boundaries, and abstractions (`ReservationStore`, `Notifier`).

## Step 3 · SOLID Principles Violated in P03
1. **Single Responsibility Principle (SRP):** One file (`hotel_booking.py`) mixed domain entities, storage mechanics, notification formatting, and booking rules.
2. **Open/Closed Principle (OCP):** Adding SMS required opening `BookingService` and editing its constructor and `reserve()` method.
3. **Liskov Substitution Principle (LSP):** No shared contract existed for stores or notifiers, so implementations could not be substituted safely.
4. **Interface Segregation Principle (ISP):** Callers had no minimal, focused protocol for just storing reservations or just sending notifications.
5. **Dependency Inversion Principle (DIP):** High-level `BookingService` depended directly on low-level concrete classes (`InMemoryReservationStore` list and `EmailSender`) instead of abstractions.

## Step 6 · Proof Nothing Changed
- All 6 original behaviour tests pass before and after splitting into `hotel_booking/{domain,stores,notifications,booking}.py`.
- `python main.py` produces the same search, booking, clash refusal, cancellation, and 2-thread race results.
- Step 7 adds 2 tests (R6 failing notifier + SMS via `CompositeNotifier`) with zero edits to `BookingService` for SMS. Total: **8/8 green tests**.