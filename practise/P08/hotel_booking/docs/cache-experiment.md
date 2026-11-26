# Cache Experiment (P08)

## 1,000 Searches (`2026-11-12` to `2026-11-14`)

| Mode | Requests | DB Queries | Cache Hits | Cache Misses | Avg (ms) | p95 (ms) |
|---|---:|---:|---:|---:|---:|---:|
| **No cache** (`python main.py --no-cache`) | 1,000 | 2,000 | 0 | 1,000 | _fill from run_ | _fill from run_ |
| **Cache-aside, TTL 30 s** (`python main.py`) | 1,000 | 2 | 999 | 1 | _fill from run_ | _fill from run_ |

- **Observation:** Caching cuts PostgreSQL work by **99.9%** (from 2,000 queries down to 2: `list_rooms` + `list_reservations` on the single cold miss).

---

## Stale Result (Step 5 — Before Invalidation)

Running with `python main.py --no-invalidate`:
1. `GET /rooms/available?check_in=2026-12-01&check_out=2026-12-04` → returns `R7`, `R8`, `R9` and caches the result for 30 s.
2. `POST /reservations` (`docs/requests/maya-r7.json`) → `201 Created` (`R7` booked in PostgreSQL).
3. `GET /rooms/available?check_in=2026-12-01&check_out=2026-12-04` → **still lists `R7`** (stale cache hit).
4. `POST /reservations` (`docs/requests/omar-r7.json`) → **`409 Conflict`**, because `BookingService.reserve()` reads directly from PostgreSQL and never trusts the cache.

After enabling invalidation (Step 6), `POST` and `DELETE` run `INCR availability:version`, so Step 3 immediately misses the old versioned key and returns fresh availability without `R7`.

---

## Hot Key & the Next Bottleneck (Step 7)

When hundreds of guests search **`2026-12-31` to `2027-01-02`** (New Year's Eve):
- All searches hit **one hot key**: `availability:v{version}:2026-12-31:2027-01-02`.
- Redis absorbs the read storm easily, so `GET /rooms/available` stops being the bottleneck.
- Every successful booking on those dates bumps `availability:version` (cache stampede / thundering herd on the next miss) and sends write traffic straight to **`POST /reservations` and PostgreSQL**, making write contention and double-booking prevention in PostgreSQL the next bottleneck.