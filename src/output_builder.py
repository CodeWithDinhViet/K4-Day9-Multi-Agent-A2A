"""Build the required submission schema from agent handoffs."""

from decimal import Decimal
from typing import Any, Dict, List, Optional

from .models import InvestigationBundle, PolicyDecision


def decimal_number(value: Optional[Decimal]) -> Optional[float]:
    """Convert an already rounded Decimal to a JSON number."""
    return float(value) if value is not None else None


def build_payment_ids(bundle: InvestigationBundle) -> List[str]:
    order_id = bundle.case.claimed_order_id
    return [
        f"{order_id}:{row['payment_sequential']}"
        for row in bundle.payment.payment_rows[:5]
    ]


def build_evidence_ids(
    bundle: InvestigationBundle, decision: PolicyDecision
) -> List[str]:
    order_id = bundle.case.claimed_order_id
    evidence = [f"order:{order_id}"]
    evidence.extend(f"item:{item_id}" for item_id in bundle.order_product.item_ids)
    evidence.extend(
        f"payment:{payment_id}" for payment_id in build_payment_ids(bundle)
    )
    evidence.extend(
        f"seller:{party.party_id}"
        for party in decision.responsible_parties
        if party.party_type == "seller"
    )
    evidence.append(f"policy:{decision.root_cause_code}")
    return evidence[:20]


def build_output(
    bundle: InvestigationBundle, decision: PolicyDecision
) -> Dict[str, Any]:
    """Create one JSON-serializable output object in README field order."""
    order_id = bundle.case.claimed_order_id
    include_history = bundle.case.investigation_scope.include_customer_history
    include_products = bundle.case.investigation_scope.include_product_context

    handoff_rows = [
        {
            "seller_id": row.seller_id,
            "shipping_limit_at": row.shipping_limit_at or None,
            "handoff_variance_hours": decimal_number(
                row.handoff_variance_hours
            ),
            "late_handoff": row.late_handoff,
        }
        for row in bundle.delivery.seller_handoff_analysis[:3]
    ]

    return {
        "case_id": bundle.case.case_id,
        "case_assessment": {
            "primary_issue": decision.primary_issue,
            "secondary_issues": decision.secondary_issues,
            "case_status": decision.case_status,
            "confidence": 1.0,
        },
        "affected_entities": {
            "order_ids": [order_id],
            "item_ids": bundle.order_product.item_ids,
            "seller_ids": bundle.order_product.seller_ids,
            "payment_ids": build_payment_ids(bundle),
        },
        "customer_context": {
            "customer_unique_id": bundle.customer.customer_unique_id,
            "related_order_ids": (
                bundle.customer.related_order_ids if include_history else []
            ),
        },
        "product_context": {
            "product_ids": (
                bundle.order_product.product_ids if include_products else []
            ),
            "category_names": (
                bundle.order_product.category_names if include_products else []
            ),
        },
        "delivery_analysis": {
            "delivered_at": bundle.delivery.delivered_at,
            "estimated_delivery_at": bundle.delivery.estimated_delivery_at,
            "carrier_handoff_at": bundle.delivery.carrier_handoff_at,
            "delivery_variance_hours": decimal_number(
                bundle.delivery.delivery_variance_hours
            ),
            "seller_handoff_analysis": handoff_rows,
            "late_handoff_seller_ids": (
                bundle.delivery.late_handoff_seller_ids[:3]
            ),
        },
        "payment_reconciliation": {
            "currency": "BRL",
            "item_total_brl": decimal_number(bundle.payment.item_total_brl),
            "freight_total_brl": decimal_number(
                bundle.payment.freight_total_brl
            ),
            "expected_total_brl": decimal_number(
                bundle.payment.expected_total_brl
            ),
            "payment_total_brl": decimal_number(
                bundle.payment.payment_total_brl
            ),
            "difference_brl": decimal_number(bundle.payment.difference_brl),
            "reconciled": bundle.payment.reconciled,
            "payment_types": bundle.payment.payment_types,
        },
        "root_cause_analysis": {
            "ranked_causes": [
                {"cause_code": decision.root_cause_code, "rank": 1}
            ],
            "responsible_parties": [
                {
                    "party_type": party.party_type,
                    "party_id": party.party_id,
                }
                for party in decision.responsible_parties
            ],
        },
        "evidence_ids": build_evidence_ids(bundle, decision),
        "financial_resolution": {
            "currency": "BRL",
            "recommended_refund_brl": decimal_number(
                decision.recommended_refund_brl
            ),
        },
        "resolution_actions": decision.resolution_actions,
    }
