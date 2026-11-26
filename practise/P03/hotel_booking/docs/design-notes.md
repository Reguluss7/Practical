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