# ADR-002: Cache Room Availability in Redis with Versioned Keys and 30 s TTL

- **Status:** Accepted
- **Date:** 2026-11-26

## Context
Baseline measurements (1,000 searches for `2026-11-12..2026-11-14`) showed that every `GET /rooms/available` hits PostgreSQL twice (`rooms` + `reservations` = 2,000 queries), repeating identical work between bookings. We need to meet the peak search latency target (p95 ≤ 1 s) and reduce repeated database compute (S6) without ever risking a double-booking.

## Decision
1. **PostgreSQL remains the sole source of truth.** `POST /reservations` and `DELETE /reservations/{booking_id}` always read and write PostgreSQL directly and **never** read from Redis.
2. **Cache-aside on search only (`GET /rooms/available`).** Keys follow `availability:v{version}:{checkIn}:{checkOut}` with a **30-second TTL**.
3. **Version-key invalidation on writes.** Every successful booking or cancellation executes `INCR availability:version` in Redis, logically invalidating stale search entries immediately while the 30 s TTL guarantees bounded staleness even if an invalidation fails.
4. **Keep caching at the API edge (`hotel_booking/api_cache.py`).** The four domain modules (`rooms`, `reservations`, `payments`, `notifications`) remain unaware of Redis.

## Consequences
**Positive**
- Repeated searches drop from 2,000 DB queries to 2 (99.9% DB load reduction).
- Even if a guest sees a briefly stale room in search, attempting to book it safely returns `409 Conflict` from PostgreSQL.
- `INCR availability:version` avoids expensive `KEYS`/`SCAN` wildcard deletes in Redis.

**Trade-offs**
- A single global `availability:version` invalidates all cached date ranges on any booking or cancellation, causing extra cold misses under heavy write load (especially on hot dates like New Year's Eve).
- Adds Redis as an operational dependency for the web app.