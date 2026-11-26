from __future__ import annotations

from . import PaymentRequest, PaymentResult


class SimulatedPaymentGateway:
    """Charges a 30% deposit in memory without hitting a real payment provider."""

    def __init__(self, deposit_rate: float = 0.30) -> None:
        self._deposit_rate = deposit_rate
        self._next_tx = 1
        self.recorded_payments: list[PaymentResult] = []

    def charge_deposit(self, request: PaymentRequest) -> PaymentResult:
        tx_id = f"TX-{self._next_tx:04d}"
        self._next_tx += 1
        deposit = round(request.total_price * self._deposit_rate, 2)
        result = PaymentResult(transaction_id=tx_id, deposit_amount=deposit, paid=True)
        self.recorded_payments.append(result)
        return result