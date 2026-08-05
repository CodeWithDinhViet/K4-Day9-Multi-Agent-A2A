"""Payment aggregation and order-total reconciliation."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Iterable

from ..data_repository import OlistRepository, Row
from ..models import PaymentAnalysis
from .order_product_agent import stable_unique


CENT = Decimal("0.01")
RECONCILIATION_TOLERANCE = Decimal("0.10")


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def sum_decimal(rows: Iterable[Row], field: str) -> Decimal:
    return sum((Decimal(row[field]) for row in rows), start=Decimal("0"))


class PaymentAgent:
    def __init__(self, repository: OlistRepository) -> None:
        self.repository = repository

    def investigate(self, order_id: str) -> PaymentAnalysis:
        items = self.repository.get_order_items(order_id)
        payments = self.repository.get_order_payments(order_id)
        payment_total = money(sum_decimal(payments, "payment_value"))
        payment_types = stable_unique(row["payment_type"] for row in payments)

        if not items:
            return PaymentAnalysis(
                payment_rows=payments,
                item_total_brl=None,
                freight_total_brl=None,
                expected_total_brl=None,
                payment_total_brl=payment_total,
                difference_brl=None,
                reconciled=None,
                payment_types=payment_types,
                split_payment=len(payments) >= 2,
            )

        item_total = money(sum_decimal(items, "price"))
        freight_total = money(sum_decimal(items, "freight_value"))
        expected_total = money(item_total + freight_total)
        difference = money(payment_total - expected_total)
        return PaymentAnalysis(
            payment_rows=payments,
            item_total_brl=item_total,
            freight_total_brl=freight_total,
            expected_total_brl=expected_total,
            payment_total_brl=payment_total,
            difference_brl=difference,
            reconciled=abs(difference) <= RECONCILIATION_TOLERANCE,
            payment_types=payment_types,
            split_payment=len(payments) >= 2,
        )

