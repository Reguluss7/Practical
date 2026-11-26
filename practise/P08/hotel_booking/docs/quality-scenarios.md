# Stakeholders & Quality Scenarios (S1–S6)

## Stakeholders

| Stakeholder | What they care about |
|---|---|
| **Guest** | Fast room search, accurate prices, instant confirmation, never arriving to a double-booked room. |
| **Hotel Reception / Staff** | Clear room availability, taking rooms out of service for repairs, handling cancellations cleanly. |
| **Hotel Owner / Finance** | Collecting deposits, accurate pricing per room tier, no lost revenue or unrecorded refunds. |
| **Backend Developer** | Changing storage (list → PostgreSQL) or adding features (SMS, deposits) without breaking booking rules. |
| **Operations / On-Call** | Third-party outages (SMTP, SMS, payment gateway) never crash or corrupt confirmed bookings. |

---

## Quality Scenarios (S1–S6)

### S1 — Concurrency / No Double-Booking (Correctness)
- **Source:** Two guests concurrently.
- **Stimulus:** Both attempt to book Room `301` for `2026-12-10` to `2026-12-12` at the exact same millisecond.
- **Environment:** Normal operation under concurrent load.
- **Artifact:** Reservations context & storage layer.
- **Response:** Exactly one booking succeeds; the second is refused with a clash error.
- **Measure:** **0 double-bookings** across 1,000 concurrent booking attempts for the same room and dates.

### S2 — Notification Fault Isolation (Reliability — R6)
- **Source:** External email/SMS provider.
- **Stimulus:** The provider times out or throws an error while confirming a booking.
- **Environment:** Normal booking flow during a provider outage.
- **Artifact:** Reservations & Notifications contexts.
- **Response:** The reservation remains saved as `CONFIRMED`, and delivery is marked failed (`notification_sent = False`) for retry.
- **Measure:** **100% of confirmed bookings** remain persisted when the notifier fails; **0 bookings lost**.

### S3 — Adding a Notification Channel (Modifiability)
- **Source:** Hotel management.
- **Stimulus:** Request to add a new confirmation channel (e.g., SMS or WhatsApp) alongside Email.
- **Environment:** Design/development time.
- **Artifact:** Notifications context.
- **Response:** Developer adds a new class implementing `Notifier` and wires it at startup.
- **Measure:** **0 lines changed** in `BookingService` and **less than 1 hour** to implement and test.

### S4 — Swapping Persistence to PostgreSQL (Modifiability / Portability)
- **Source:** Engineering team (P07 milestone).
- **Stimulus:** Replace `InMemoryReservationStore` with `PostgresReservationStore`.
- **Environment:** Development / deployment time.
- **Artifact:** Storage adapter behind `ReservationStore`.
- **Response:** New store implements `ReservationStore`; domain and booking rules remain untouched.
- **Measure:** **0 lines changed** in `BookingService` and `domain.py`; all existing unit tests remain green.

### S5 — Availability Search Speed (Performance)
- **Source:** Guest or reception desk.
- **Stimulus:** Search available rooms for a date range across 500 rooms and 50,000 stored reservations.
- **Environment:** Peak booking hours (50 concurrent searches/second).
- **Artifact:** Rooms & Reservations query path.
- **Response:** System returns matching free rooms filtered by date and room type.
- **Measure:** **95th percentile (p95) response time under 200 ms**.

### S6 — Booking & Cancellation Auditability (Traceability)
- **Source:** Hotel staff or finance auditor.
- **Stimulus:** Guest disputes a cancelled stay or missing confirmation.
- **Environment:** Post-incident review.
- **Artifact:** Reservations, Payments, and Notifications records.
- **Response:** System retains full guest history including `CANCELLED` bookings, timestamps, payment status, and delivery status.
- **Measure:** **100% of past bookings** (confirmed and cancelled) are retrievable by `guest_id` with no destructive deletes.