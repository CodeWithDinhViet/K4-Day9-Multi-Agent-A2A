"""Typed contracts shared by the coordinator and domain agents."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class InvestigationScope:
    include_customer_history: bool
    include_product_context: bool


@dataclass(frozen=True)
class CaseInput:
    case_id: str
    language: str
    message: str
    claimed_order_id: str
    investigation_scope: InvestigationScope
    policy_version: str

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "CaseInput":
        request = payload["customer_request"]
        scope = payload["investigation_scope"]
        return cls(
            case_id=str(payload["case_id"]),
            language=str(request["language"]),
            message=str(request["message"]),
            claimed_order_id=str(request["claimed_order_id"]),
            investigation_scope=InvestigationScope(
                include_customer_history=bool(scope["include_customer_history"]),
                include_product_context=bool(scope["include_product_context"]),
            ),
            policy_version=str(payload["policy_version"]),
        )


@dataclass(frozen=True)
class CustomerAnalysis:
    customer_unique_id: str
    related_order_ids: List[str]
    repeat_customer: bool


@dataclass(frozen=True)
class OrderProductAnalysis:
    order: Dict[str, str]
    item_rows: List[Dict[str, str]]
    item_ids: List[str]
    seller_ids: List[str]
    product_ids: List[str]
    category_names: List[str]
    multi_item_order: bool
    multi_seller_order: bool
    multiple_categories: bool


@dataclass(frozen=True)
class PaymentAnalysis:
    payment_rows: List[Dict[str, str]]
    item_total_brl: Optional[Decimal]
    freight_total_brl: Optional[Decimal]
    expected_total_brl: Optional[Decimal]
    payment_total_brl: Decimal
    difference_brl: Optional[Decimal]
    reconciled: Optional[bool]
    payment_types: List[str]
    split_payment: bool


@dataclass(frozen=True)
class SellerHandoff:
    seller_id: str
    shipping_limit_at: str
    handoff_variance_hours: Optional[Decimal]
    late_handoff: bool


@dataclass(frozen=True)
class DeliveryAnalysis:
    delivered_at: Optional[str]
    estimated_delivery_at: Optional[str]
    carrier_handoff_at: Optional[str]
    delivery_variance_hours: Optional[Decimal]
    late_delivery: bool
    seller_handoff_analysis: List[SellerHandoff]
    late_handoff_seller_ids: List[str]


@dataclass(frozen=True)
class InvestigationBundle:
    case: CaseInput
    customer: CustomerAnalysis
    order_product: OrderProductAnalysis
    payment: PaymentAnalysis
    delivery: DeliveryAnalysis
