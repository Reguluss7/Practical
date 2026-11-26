from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel

from hotel_booking.reservations import BookingService, Guest
from hotel_booking.rooms import RoomType


class ReserveRequest(BaseModel):
    room_number: str
    guest_id: str
    guest_name: str
    guest_email: str
    guest_phone: str = ""
    check_in: date
    check_out: date


def create_app(service: BookingService, openapi_path: Optional[Path] = None) -> FastAPI:
    app = FastAPI(title="Hotel Booking API", version="1.0.0")
    spec_file = openapi_path or Path(__file__).resolve().parent.parent / "docs" / "openapi.yaml"

    @app.get("/openapi.yaml", include_in_schema=False)
    def get_openapi_yaml() -> FileResponse:
        if not spec_file.exists():
            raise HTTPException(status_code=404, detail="openapi.yaml not found")
        return FileResponse(spec_file, media_type="application/yaml")

    @app.get("/rooms/available")
    def search_available_rooms(
        check_in: date,
        check_out: date,
        room_type: Optional[str] = None,
        limit: int = Query(default=10, ge=1, le=100),
        after: Optional[str] = None,
    ) -> dict:
        parsed_type: Optional[RoomType] = None
        if room_type is not None:
            try:
                parsed_type = RoomType(room_type.upper())
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"Invalid room_type: {room_type}") from exc

        try:
            rooms = service.find_available_rooms(check_in, check_out, parsed_type)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        rooms.sort(key=lambda r: r.room_number)
        if after is not None:
            rooms = [r for r in rooms if r.room_number > after]

        page = rooms[:limit]
        next_after = page[-1].room_number if len(rooms) > limit else None

        return {
            "rooms": [
                {
                    "room_number": r.room_number,
                    "room_type": r.room_type.value,
                    "nightly_rate": r.nightly_rate,
                }
                for r in page
            ],
            "next_after": next_after,
        }

    @app.post("/reservations", status_code=201)
    def create_reservation(payload: ReserveRequest) -> dict:
        guest = Guest(
            guest_id=payload.guest_id,
            name=payload.guest_name,
            email=payload.guest_email,
            phone=payload.guest_phone,
        )
        try:
            res = service.reserve(
                room_number=payload.room_number,
                guest=guest,
                check_in=payload.check_in,
                check_out=payload.check_out,
            )
        except ValueError as exc:
            msg = str(exc)
            if "not available" in msg:
                raise HTTPException(status_code=409, detail=msg) from exc
            if "does not exist" in msg:
                raise HTTPException(status_code=404, detail=msg) from exc
            raise HTTPException(status_code=400, detail=msg) from exc

        return {
            "booking_id": res.booking_id,
            "room_number": res.room.room_number,
            "guest_id": res.guest.guest_id,
            "check_in": res.check_in.isoformat(),
            "check_out": res.check_out.isoformat(),
            "nights": res.nights,
            "total_price": res.total_price,
            "deposit_paid": res.deposit_paid,
            "status": res.status.value,
            "notification_sent": res.notification_sent,
        }

    @app.delete("/reservations/{booking_id}", status_code=204)
    def cancel_reservation(booking_id: str) -> Response:
        try:
            service.cancel(booking_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return Response(status_code=204)

    return app