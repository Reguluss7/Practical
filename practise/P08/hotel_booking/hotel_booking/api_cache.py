from __future__ import annotations

import json
import time
from datetime import date
from typing import Optional, Protocol

import redis

from hotel_booking.rooms import Room, RoomType


class AvailabilityCache(Protocol):
    @property
    def hits(self) -> int: ...

    @property
    def misses(self) -> int: ...

    def current_version(self) -> int: ...
    def get(self, check_in: date, check_out: date) -> Optional[list[Room]]: ...
    def set(self, check_in: date, check_out: date, rooms: list[Room]) -> None: ...
    def invalidate(self) -> int: ...


def _serialize_rooms(rooms: list[Room]) -> str:
    return json.dumps(
        [
            {
                "room_number": r.room_number,
                "room_type": r.room_type.value,
                "nightly_rate": r.nightly_rate,
            }
            for r in rooms
        ]
    )


def _deserialize_rooms(raw: str) -> list[Room]:
    items = json.loads(raw)
    return [
        Room(
            room_number=item["room_number"],
            room_type=RoomType(item["room_type"]),
            nightly_rate=float(item["nightly_rate"]),
        )
        for item in items
    ]


class NoOpAvailabilityCache:
    """Used in Step 1 (--no-cache) to measure baseline PostgreSQL performance."""

    def __init__(self) -> None:
        self._hits = 0
        self._misses = 0

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    def current_version(self) -> int:
        return 0

    def get(self, check_in: date, check_out: date) -> Optional[list[Room]]:
        self._misses += 1
        return None

    def set(self, check_in: date, check_out: date, rooms: list[Room]) -> None:
        pass

    def invalidate(self) -> int:
        return 0


class InMemoryAvailabilityCache:
    """In-memory cache-aside with TTL and version key for fast unit tests."""

    def __init__(self, ttl_seconds: int = 30) -> None:
        self._ttl = ttl_seconds
        self._version = 1
        self._data: dict[str, tuple[float, str]] = {}
        self._hits = 0
        self._misses = 0

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    def current_version(self) -> int:
        return self._version

    def _key(self, check_in: date, check_out: date) -> str:
        return f"availability:v{self._version}:{check_in.isoformat()}:{check_out.isoformat()}"

    def get(self, check_in: date, check_out: date) -> Optional[list[Room]]:
        key = self._key(check_in, check_out)
        entry = self._data.get(key)
        if entry is None or time.monotonic() > entry[0]:
            self._data.pop(key, None)
            self._misses += 1
            return None
        self._hits += 1
        return _deserialize_rooms(entry[1])

    def set(self, check_in: date, check_out: date, rooms: list[Room]) -> None:
        key = self._key(check_in, check_out)
        self._data[key] = (time.monotonic() + self._ttl, _serialize_rooms(rooms))

    def invalidate(self) -> int:
        self._version += 1
        return self._version


class RedisAvailabilityCache:
    """Redis cache-aside: availability:v{version}:{checkIn}:{checkOut}, TTL 30s."""

    VERSION_KEY = "availability:version"

    def __init__(self, redis_url: str, ttl_seconds: int = 30) -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._ttl = ttl_seconds
        self._hits = 0
        self._misses = 0

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    def current_version(self) -> int:
        val = self._client.get(self.VERSION_KEY)
        if val is None:
            self._client.setnx(self.VERSION_KEY, 1)
            return 1
        return int(val)

    def _key(self, check_in: date, check_out: date) -> str:
        version = self.current_version()
        return f"availability:v{version}:{check_in.isoformat()}:{check_out.isoformat()}"

    def get(self, check_in: date, check_out: date) -> Optional[list[Room]]:
        raw = self._client.get(self._key(check_in, check_out))
        if raw is None:
            self._misses += 1
            return None
        self._hits += 1
        return _deserialize_rooms(raw)

    def set(self, check_in: date, check_out: date, rooms: list[Room]) -> None:
        self._client.setex(
            self._key(check_in, check_out),
            self._ttl,
            _serialize_rooms(rooms),
        )

    def invalidate(self) -> int:
        return int(self._client.incr(self.VERSION_KEY))