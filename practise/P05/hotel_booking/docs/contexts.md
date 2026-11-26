# Bounded Contexts & Domain Ownership

## Words (from R1–R6 and P04 Code)

`Room`, `RoomNumber`, `RoomType` (`SINGLE`, `DOUBLE`, `SUITE`, `DELUXE`), `NightlyRate`, `OutOfService`, `Availability`, `Stay`, `CheckIn`, `CheckOut`, `Nights`, `Booking` / `Reservation`, `BookingId`, `Guest`, `Overlap` / `Clash`, `Confirmed`, `Cancelled`, `TotalPrice`, `Deposit` (30%), `Paid`, `Refund`, `Notification`, `Email`, `SMS`, `Sent`, `Failed`, `Recipient`.

---

## Four Bounded Contexts

### 1. Rooms
- **Job:** Owns the hotel's physical room inventory, room tiers, base nightly pricing, and operational status (active vs. out of service for repairs).
- **Words:** `Room`, `RoomNumber`, `RoomType`, `NightlyRate`, `OutOfService`, `MaintenanceWindow`.

### 2. Reservations
- **Job:** Owns stays, date-range rules (`check_out > check_in`), overlap/clash prevention, booking lifecycle (`CONFIRMED` / `CANCELLED`), and guest booking history.
- **Words:** `Reservation`, `BookingId`, `Guest`, `Stay`, `CheckIn`, `CheckOut`, `Nights`, `Overlap`, `Clash`, `Confirmed`, `Cancelled`, `Availability`.

### 3. Payments
- **Job:** Owns money movement—calculating and collecting deposits (e.g., 30%), recording balances, and issuing refunds when a reservation is cancelled.
- **Words:** `TotalPrice`, `Deposit`, `Charge`, `Paid`, `Unpaid`, `Refund`, `PaymentStatus`, `TransactionId`.

### 4. Notifications
- **Job:** Owns formatting and delivering guest messages across channels (Email, SMS) and tracking delivery outcomes without affecting booking persistence.
- **Words:** `Notification`, `Email`, `SMS`, `Recipient`, `Message`, `Sent`, `Failed`, `Retry`.

---

## Same Word, Different Meaning

| Word | Context A | Context B |
|---|---|---|
| **Room** | **Rooms:** A physical asset with type (`SUITE`), nightly rate, and repair/maintenance status. | **Reservations:** Just a `room_number` reference that a calendar interval is booked against. |
| **Cancel** | **Reservations:** Releases the date range and flips booking status from `CONFIRMED` to `CANCELLED`. | **Payments:** Triggers a refund policy check and reverses or retains the deposit. |
| **Confirmed / Paid / Sent** | **Reservations (`Confirmed`):** The room is held for those dates. | **Payments (`Paid`):** Money/deposit was captured. **Notifications (`Sent`):** Message left the gateway. A booking can be `Confirmed` even if `Sent` is `False` (R6). |
| **Guest** | **Reservations:** Identity (`guest_id`, `name`) tied to booking history. | **Notifications:** Reachable contact endpoints (`email`, `phone`). **Payments:** Billing payer. |

---

## Rule Owners (8 Rule Cards)

| # | Rule | Owner | Reason |
|---|---|---|---|
| 1 | **Unique room numbers & positive nightly rates (R1)** | **Rooms** | Inventory integrity and pricing tiers belong solely to the room catalog. |
| 2 | **Room out of service for repairs cannot be offered** | **Rooms** | Only Rooms knows maintenance schedules and operational readiness. |
| 3 | **Deluxe / Suite rooms cost more per night** | **Rooms** | Nightly rate schedules and room-type pricing live in the catalog, not booking logic. |
| 4 | **Valid stay dates (`check_out > check_in`) & back-to-back allowed (R2)** | **Reservations** | Date-interval semantics define what constitutes a valid stay. |
| 5 | **No overlapping confirmed bookings for the same room (R3)** | **Reservations** | Preventing double-booking is the core invariant of the Reservations context. |
| 6 | **Cancelling frees dates; double-cancel is rejected (R4, R5)** | **Reservations** | Owns the reservation state machine and booking history. |
| 7 | **Take a 30% deposit on booking & handle refund on cancel** | **Payments** | Financial rules, payment gateways, and refund policies must stay isolated from calendar logic. |
| 8 | **Send Email/SMS confirmations; delivery failure never loses a booking (R6)** | **Notifications** | Channel formatting, fan-out, and retries belong to Notifications; Reservations only emits the event. |

---

## Between Contexts (What Crosses Each Border)

| # | Arrow (From → To) | Kind | Name | Fields Crossing the Border |
|---|---|---|---|---|
| 1 | **Reservations → Rooms** | **Question (Query)** | `GetRoomDetails` / `ListBookableRooms` | **Request:** `room_number` (or `room_type`, `check_in`, `check_out`) <br> **Reply:** `room_number`, `room_type`, `nightly_rate`, `is_available_for_service` |
| 2 | **Reservations → Payments** | **Event** | `ReservationConfirmed` | `booking_id`, `guest_id`, `room_number`, `nights`, `total_price`, `currency`, `confirmed_at` |
| 3 | **Reservations → Payments** | **Event** | `ReservationCancelled` | `booking_id`, `guest_id`, `check_in`, `cancelled_at` |
| 4 | **Reservations → Notifications** | **Event** | `ReservationConfirmed` | `booking_id`, `guest_name`, `guest_email`, `guest_phone`, `room_number`, `check_in`, `check_out`, `total_price` |
| 5 | **Reservations → Notifications** | **Event** | `ReservationCancelled` | `booking_id`, `guest_name`, `guest_email`, `guest_phone`, `room_number`, `check_in`, `check_out` |
| 6 | **Payments → Notifications** | **Event** | `DepositCharged` / `RefundIssued` | `transaction_id`, `booking_id`, `guest_email`, `guest_phone`, `amount`, `status` (`PAID` / `REFUNDED`) |