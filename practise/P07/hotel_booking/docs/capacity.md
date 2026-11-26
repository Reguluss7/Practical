# Capacity Estimate (P07)

## Assumptions
- **Peak search load (S1):** 200 guests searching within 1 minute.
- **Search-to-booking ratio:** 10:1 (20 bookings/minute at peak).
- **Hotel size:** 500 rooms, average 200 bookings/day (~73,000 bookings/year).
- **Average payload sizes:**
  - Search response (10 rooms JSON): ~1.5 KB
  - Reservation request + response JSON: ~0.6 KB
  - Stored reservation row (with indexes): ~500 bytes

## Calculations
- **Requests per second (RPS):**
  - Peak searches: `200 / 60 = 3.33 req/s`
  - Peak bookings: `20 / 60 = 0.33 req/s`
  - Total peak RPS: **~3.7 req/s** (easily handled by 1 FastAPI/Uvicorn worker + 1 PostgreSQL instance).
- **Storage (5 years):**
  - `73,000 rows/year * 5 years = 365,000 rows`
  - `365,000 * 500 bytes ≈ 182.5 MB` (plus ~100 KB for `rooms` and WAL overhead → **less than 250 MB**).
- **Bandwidth (Peak):**
  - Search egress: `3.33 req/s * 1.5 KB ≈ 5 KB/s`
  - Booking traffic: `0.33 req/s * 0.6 KB ≈ 0.2 KB/s`
  - Total peak bandwidth: **~5.2 KB/s** (~42 Kbps).

## What to Measure Later
1. **p95 search latency** on `GET /rooms/available` as `reservations` grows past 50,000 rows (verify `idx_reservations_room_dates` is used via `EXPLAIN ANALYZE`).
2. **Concurrent clash rate** when two app instances book the same room simultaneously (to validate DB-level locking/exclusion constraints in the next step).
3. **Database connection pool saturation** under bursty traffic.