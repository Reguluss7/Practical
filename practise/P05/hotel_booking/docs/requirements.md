# Hotel Booking App — Requirements (R1–R5)

## Functional Requirements

### R1 — Room Inventory
The system must allow adding rooms with a unique `room_number`, a `room_type` (`SINGLE`, `DOUBLE`, `SUITE`), and a positive `nightly_rate`. Duplicate room numbers must be rejected.

### R2 — Availability Search
The system must return all rooms available for a given `[check_in, check_out)` date range, with an optional filter by `room_type`.
- `check_out` must be strictly after `check_in`.
- Back-to-back bookings (previous `check_out == next check_in`) are allowed.

### R3 — Room Booking & Price Calculation
A guest must be able to book an available room for a valid date range.
- Total price = `(check_out - check_in).days * room.nightly_rate`.
- Double-booking an already confirmed overlapping date range must be rejected.
- Each confirmed booking receives a unique `booking_id` (e.g., `BK-0001`).

### R4 — Booking Cancellation
A confirmed booking can be cancelled by its `booking_id`.
- Cancelling changes its status from `CONFIRMED` to `CANCELLED`.
- Cancelled dates immediately become available for new bookings.
- Cancelling a non-existent or already cancelled booking must be rejected.

### R5 — Guest Booking History
The system must allow listing all bookings (both `CONFIRMED` and `CANCELLED`) associated with a specific `guest_id`.

---

## Concrete Examples

1. **Standard booking:** Guest `G1` books Room `101` (`SINGLE`, `$80/night`) from `2026-12-01` to `2026-12-04` (3 nights) → `CONFIRMED`, total `$240.00`.
2. **Double-booking blocked:** Guest `G2` attempts to book Room `101` from `2026-12-03` to `2026-12-05` → rejected (`ValueError: Room 101 is not available`).
3. **Back-to-back allowed:** Guest `G2` books Room `101` from `2026-12-04` to `2026-12-06` → `CONFIRMED` (starts on the day `G1` checks out).
4. **Cancel & re-book:** `G1` cancels `BK-0001` → status becomes `CANCELLED`, and `G2` can now book Room `101` from `2026-12-01` to `2026-12-04`.

---

## Proof Lines (Acceptance Criteria)

- **P1 (R1):** Adding room `101` succeeds; adding `101` again raises `ValueError`.
- **P2 (R2):** Searching `2026-12-01` to `2026-12-04` excludes booked room `101` and includes unbooked room `201`.
- **P3 (R3):** Booking `101` for 3 nights at `$80` produces `total_price == 240.0`; overlapping booking raises `ValueError`; back-to-back booking (`12-04` to `12-06`) succeeds.
- **P4 (R4):** Cancelling `BK-0001` sets `status == CANCELLED` and makes `101` available again for `12-01` to `12-04`; cancelling `BK-0001` a second time raises `ValueError`.
- **P5 (R5):** Querying bookings for `G1` returns `BK-0001` with status `CANCELLED`.

### R6 — Notification Failure Isolation (Added in P04)
A failure in sending a booking confirmation (e.g., email or SMS outage) must never lose or roll back a confirmed reservation.
- The reservation must remain saved in the store with `status == CONFIRMED`.
- Delivery status is recorded (`notification_sent = False`) without aborting the reservation.

#### Proof Line
- **P6 (R6):** Reserving with a `FailingNotifier` that raises `RuntimeError` still persists the `CONFIRMED` reservation in the store and sets `notification_sent == False`.