"""Delivery lateness and per-seller carrier-handoff analysis."""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Optional

from ..data_repository import OlistRepository
from ..models import DeliveryAnalysis, SellerHandoff
from .order_product_agent import stable_unique


TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"
HUNDREDTH = Decimal("0.01")


def parse_timestamp(value: str) -> Optional[datetime]:
    return datetime.strptime(value, TIMESTAMP_FORMAT) if value else None


def hours_between(later: datetime, earlier: datetime) -> Decimal:
    hours = Decimal(str((later - earlier).total_seconds())) / Decimal("3600")
    return hours.quantize(HUNDREDTH, rounding=ROUND_HALF_UP)


class DeliveryAgent:
    def __init__(self, repository: OlistRepository) -> None:
        self.repository = repository

    def investigate(self, order_id: str) -> DeliveryAnalysis:
        order = self.repository.get_order(order_id)
        if order is None:
            raise ValueError(f"Order {order_id!r} was not found")

        delivered = parse_timestamp(order["order_delivered_customer_date"])
        estimated = parse_timestamp(order["order_estimated_delivery_date"])
        carrier_handoff = parse_timestamp(order["order_delivered_carrier_date"])
        delivery_variance = (
            hours_between(delivered, estimated)
            if delivered is not None and estimated is not None
            else None
        )

        items = self.repository.get_order_items(order_id)
        earliest_limit_by_seller: Dict[str, str] = {}
        for item in items:
            seller_id = item["seller_id"]
            limit = item["shipping_limit_date"]
            current = earliest_limit_by_seller.get(seller_id)
            if limit and (current is None or limit < current):
                earliest_limit_by_seller[seller_id] = limit

        seller_order = stable_unique(item["seller_id"] for item in items)
        handoffs = []
        for seller_id in seller_order:
            limit_text = earliest_limit_by_seller.get(seller_id, "")
            limit = parse_timestamp(limit_text)
            variance = (
                hours_between(carrier_handoff, limit)
                if carrier_handoff is not None and limit is not None
                else None
            )
            handoffs.append(
                SellerHandoff(
                    seller_id=seller_id,
                    shipping_limit_at=limit_text,
                    handoff_variance_hours=variance,
                    late_handoff=variance is not None and variance > 0,
                )
            )

        late_sellers = [row.seller_id for row in handoffs if row.late_handoff]
        return DeliveryAnalysis(
            delivered_at=order["order_delivered_customer_date"] or None,
            estimated_delivery_at=order["order_estimated_delivery_date"] or None,
            carrier_handoff_at=order["order_delivered_carrier_date"] or None,
            delivery_variance_hours=delivery_variance,
            late_delivery=delivery_variance is not None and delivery_variance > 0,
            seller_handoff_analysis=handoffs,
            late_handoff_seller_ids=late_sellers,
        )

