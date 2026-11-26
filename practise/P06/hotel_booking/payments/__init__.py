from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class PaymentRequest:
    booking_id: str
    guest_id: str
    total_price: float


@dataclass(frozen=True)
class PaymentResult:
    transaction_id: str
    deposit_amount: float
    paid: bool


class PaymentGateway(Protocol):
    def charge_deposit(self, request: PaymentRequest) -> PaymentResult: ...


__all__ = ["PaymentGateway", "PaymentRequest", "PaymentResult"]