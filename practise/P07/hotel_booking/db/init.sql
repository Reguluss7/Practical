CREATE TABLE IF NOT EXISTS rooms (
    room_number  TEXT PRIMARY KEY,
    room_type    TEXT NOT NULL CHECK (room_type IN ('SINGLE', 'DOUBLE', 'SUITE')),
    nightly_rate NUMERIC(10, 2) NOT NULL CHECK (nightly_rate > 0)
);

CREATE TABLE IF NOT EXISTS reservations (
    booking_id        TEXT PRIMARY KEY,
    room_number       TEXT NOT NULL REFERENCES rooms(room_number),
    guest_id          TEXT NOT NULL,
    guest_name        TEXT NOT NULL,
    guest_email       TEXT NOT NULL,
    guest_phone       TEXT NOT NULL DEFAULT '',
    check_in          DATE NOT NULL,
    check_out         DATE NOT NULL,
    status            TEXT NOT NULL CHECK (status IN ('CONFIRMED', 'CANCELLED')),
    notification_sent BOOLEAN NOT NULL DEFAULT TRUE,
    deposit_paid      NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    CHECK (check_out > check_in)
);

CREATE INDEX IF NOT EXISTS idx_reservations_room_dates
    ON reservations (room_number, check_in, check_out)
    WHERE status = 'CONFIRMED';

INSERT INTO rooms (room_number, room_type, nightly_rate) VALUES
    ('R7', 'DOUBLE', 120.00),
    ('R8', 'SUITE', 200.00),
    ('R9', 'SINGLE', 80.00)
ON CONFLICT (room_number) DO NOTHING;D