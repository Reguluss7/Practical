# ADR-001: Organize the Hotel Booking App as a Modular Monolith

- **Status:** Accepted
- **Date:** 2026-11-26

## Context
In P04 we decoupled `BookingService` from concrete storage and email classes using protocols, and in P05 we mapped four business areas (`Rooms`, `Reservations`, `Payments`, `Notifications`). However, the codebase still had three structural risks:
1. Nothing stopped `BookingService` from importing concrete classes like `EmailSender` directly.
2. `Notifier` accepted the `Reservation` class directly, coupling `Notifications` to `Reservations`.
3. `Payments` existed only on paper with no code boundary.

We need enforceable module boundaries now, without the deployment and network overhead of distributed microservices.

## Decision
Structure `hotel_booking/` as a **modular monolith** with four top-level packages—`rooms`, `reservations`, `payments`, and `notifications`—following three rules:
1. **Public contracts vs. internal code:** Each module exposes only its public protocols and value objects at the package root (`__init__.py`, `catalog.py`, `domain.py`, `booking.py`). Concrete implementations live in `internal.py`.
2. **One composition root:** `main.py` (and tests) are the only files allowed to import `*.internal` classes and wire them together.
3. **Automated border enforcement:** Three `import-linter` contracts in `pyproject.toml` fail the check if `Reservations` reaches into another module's `internal.py`, if supporting modules import `Reservations`, or if supporting modules depend on each other.

## Consequences
**Positive**
- Module borders are verified automatically on every change (`lint-imports`), not just documented in Markdown.
- `Notifications` uses its own `Confirmation` message, breaking its dependency on `Reservations`.
- Swapping `InMemoryReservationStore` for PostgreSQL in P07 or replacing `SimulatedPaymentGateway` touches only one `internal.py` and `main.py`.
- Single process, single test command, zero network latency or distributed transaction complexity.

**Trade-offs**
- Slightly more files and boilerplate (e.g., mapping `Reservation` to `Confirmation` and `PaymentRequest` at module borders).
- All modules still share one deployment unit until scale or team size justifies extracting a service.

## Alternatives Considered
- **Flat package with naming conventions only:** Rejected because conventions drift without automated import checks.
- **Four separate microservices:** Rejected as premature for a single team and current traffic; adds network failure modes and deployment overhead before domain boundaries are proven.