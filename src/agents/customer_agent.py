"""Customer identity and purchase-history analysis."""

from ..data_repository import OlistRepository
from ..models import CustomerAnalysis


class CustomerAgent:
    def __init__(self, repository: OlistRepository) -> None:
        self.repository = repository

    def investigate(self, order_id: str) -> CustomerAnalysis:
        order = self.repository.get_order(order_id)
        if order is None:
            raise ValueError(f"Order {order_id!r} was not found")

        customer = self.repository.get_customer(order["customer_id"])
        if customer is None:
            raise ValueError(
                f"Customer {order['customer_id']!r} for order {order_id!r} was not found"
            )

        unique_id = customer["customer_unique_id"]
        related_ids = [
            row["order_id"]
            for row in self.repository.get_customer_history(unique_id)
            if row["order_id"] != order_id
        ]
        return CustomerAnalysis(
            customer_unique_id=unique_id,
            related_order_ids=related_ids[:5],
            repeat_customer=bool(related_ids),
        )

