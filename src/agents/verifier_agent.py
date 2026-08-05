"""Final validation gate for one submission-shaped case output."""

import re
from typing import Any, Dict, List

from ..data_repository import OlistRepository
from ..models import InvestigationBundle, PolicyDecision


EVIDENCE_PATTERN = re.compile(
    r"^(order:[^:]+|item:[^:]+:[^:]+|payment:[^:]+:[^:]+|"
    r"seller:[^:]+|policy:[A-Z_]+)$"
)

SECONDARY_ORDER = [
    "multi_item_order",
    "multi_seller_order",
    "split_payment",
    "repeat_customer",
    "multiple_categories",
]

TOP_LEVEL_KEYS = [
    "case_id",
    "case_assessment",
    "affected_entities",
    "customer_context",
    "product_context",
    "delivery_analysis",
    "payment_reconciliation",
    "root_cause_analysis",
    "evidence_ids",
    "financial_resolution",
    "resolution_actions",
]


class VerificationError(ValueError):
    """Raised when a case would fail the submission contract."""


class VerifierAgent:
    def __init__(self, repository: OlistRepository) -> None:
        self.repository = repository

    def verify(
        self,
        output: Dict[str, Any],
        bundle: InvestigationBundle,
        decision: PolicyDecision,
    ) -> None:
        errors: List[str] = []
        self._check_schema(output, errors)
        self._check_limits(output, errors)
        self._check_policy(output, decision, errors)
        self._check_entities(output, bundle, errors)
        self._check_evidence(output, bundle, decision, errors)
        self._check_null_handling(output, bundle, errors)
        if errors:
            joined = "; ".join(errors)
            raise VerificationError(f"{bundle.case.case_id}: {joined}")

    @staticmethod
    def _check_schema(output: Dict[str, Any], errors: List[str]) -> None:
        if list(output) != TOP_LEVEL_KEYS:
            errors.append("top-level fields or field order do not match schema")
        assessment = output.get("case_assessment", {})
        confidence = assessment.get("confidence")
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            errors.append("confidence must be a number in [0, 1]")
        if assessment.get("case_status") not in {"action_required", "no_action"}:
            errors.append("invalid case_status")
        if output.get("financial_resolution", {}).get("currency") != "BRL":
            errors.append("financial currency must be BRL")
        if output.get("payment_reconciliation", {}).get("currency") != "BRL":
            errors.append("payment currency must be BRL")

    @staticmethod
    def _check_limits(output: Dict[str, Any], errors: List[str]) -> None:
        entities = output.get("affected_entities", {})
        checks = [
            (entities.get("order_ids", []), 5, "order_ids"),
            (entities.get("item_ids", []), 5, "item_ids"),
            (entities.get("seller_ids", []), 3, "seller_ids"),
            (entities.get("payment_ids", []), 5, "payment_ids"),
            (output.get("customer_context", {}).get("related_order_ids", []), 5, "related_order_ids"),
            (output.get("product_context", {}).get("product_ids", []), 5, "product_ids"),
            (output.get("product_context", {}).get("category_names", []), 5, "category_names"),
            (output.get("root_cause_analysis", {}).get("ranked_causes", []), 3, "ranked_causes"),
            (output.get("root_cause_analysis", {}).get("responsible_parties", []), 3, "responsible_parties"),
            (output.get("evidence_ids", []), 20, "evidence_ids"),
            (output.get("resolution_actions", []), 5, "resolution_actions"),
        ]
        for values, limit, name in checks:
            if not isinstance(values, list) or len(values) > limit:
                errors.append(f"{name} exceeds limit {limit} or is not an array")

    @staticmethod
    def _check_policy(
        output: Dict[str, Any], decision: PolicyDecision, errors: List[str]
    ) -> None:
        assessment = output.get("case_assessment", {})
        if assessment.get("primary_issue") != decision.primary_issue:
            errors.append("primary_issue differs from policy decision")
        secondary = assessment.get("secondary_issues", [])
        if secondary != decision.secondary_issues:
            errors.append("secondary_issues differ from policy decision")
        indexes = [SECONDARY_ORDER.index(value) for value in secondary]
        if indexes != sorted(indexes):
            errors.append("secondary_issues are not in policy order")
        refund = output.get("financial_resolution", {}).get(
            "recommended_refund_brl"
        )
        if refund != float(decision.recommended_refund_brl):
            errors.append("refund differs from policy decision")
        if output.get("resolution_actions") != decision.resolution_actions:
            errors.append("resolution_actions differ from policy decision")
        expected_status = "action_required" if refund and refund > 0 else "no_action"
        if assessment.get("case_status") != expected_status:
            errors.append("case_status is inconsistent with refund")

    def _check_entities(
        self,
        output: Dict[str, Any],
        bundle: InvestigationBundle,
        errors: List[str],
    ) -> None:
        entities = output.get("affected_entities", {})
        order_id = bundle.case.claimed_order_id
        if output.get("case_id") != bundle.case.case_id:
            errors.append("case_id differs from input")
        if entities.get("order_ids") != [order_id]:
            errors.append("affected order must contain only the claimed order")
        for item_id in entities.get("item_ids", []):
            if item_id not in bundle.order_product.item_ids:
                errors.append(f"unknown affected item {item_id}")
        for seller_id in entities.get("seller_ids", []):
            if self.repository.get_seller(seller_id) is None:
                errors.append(f"unknown seller {seller_id}")
        valid_payment_ids = {
            f"{order_id}:{row['payment_sequential']}"
            for row in bundle.payment.payment_rows
        }
        for payment_id in entities.get("payment_ids", []):
            if payment_id not in valid_payment_ids:
                errors.append(f"unknown payment {payment_id}")

    def _check_evidence(
        self,
        output: Dict[str, Any],
        bundle: InvestigationBundle,
        decision: PolicyDecision,
        errors: List[str],
    ) -> None:
        evidence = output.get("evidence_ids", [])
        order_id = bundle.case.claimed_order_id
        valid_evidence = {f"order:{order_id}"}
        valid_evidence.update(
            f"item:{item_id}" for item_id in bundle.order_product.item_ids
        )
        valid_evidence.update(
            f"payment:{order_id}:{row['payment_sequential']}"
            for row in bundle.payment.payment_rows
        )
        valid_evidence.update(
            f"seller:{party.party_id}"
            for party in decision.responsible_parties
            if party.party_type == "seller"
        )
        valid_evidence.add(f"policy:{decision.root_cause_code}")
        if len(evidence) != len(set(evidence)):
            errors.append("evidence_ids contains duplicates")
        for value in evidence:
            if not isinstance(value, str) or EVIDENCE_PATTERN.fullmatch(value) is None:
                errors.append(f"invalid evidence format {value!r}")
            elif value not in valid_evidence:
                errors.append(f"evidence is not supported by source data: {value}")
        if f"order:{order_id}" not in evidence:
            errors.append("claimed-order evidence is missing")
        cause_evidence = f"policy:{decision.root_cause_code}"
        if cause_evidence not in evidence:
            errors.append("root-cause policy evidence is missing")
        for party in decision.responsible_parties:
            if party.party_type == "seller" and f"seller:{party.party_id}" not in evidence:
                errors.append(f"responsible seller evidence missing: {party.party_id}")

    @staticmethod
    def _check_null_handling(
        output: Dict[str, Any],
        bundle: InvestigationBundle,
        errors: List[str],
    ) -> None:
        if bundle.order_product.item_rows:
            return
        payment = output.get("payment_reconciliation", {})
        for field in (
            "item_total_brl",
            "freight_total_brl",
            "expected_total_brl",
            "difference_brl",
            "reconciled",
        ):
            if payment.get(field) is not None:
                errors.append(f"{field} must be null when the order has no items")
        entities = output.get("affected_entities", {})
        product = output.get("product_context", {})
        delivery = output.get("delivery_analysis", {})
        for field, values in (
            ("item_ids", entities.get("item_ids")),
            ("seller_ids", entities.get("seller_ids")),
            ("product_ids", product.get("product_ids")),
            ("category_names", product.get("category_names")),
            ("seller_handoff_analysis", delivery.get("seller_handoff_analysis")),
            ("late_handoff_seller_ids", delivery.get("late_handoff_seller_ids")),
        ):
            if values != []:
                errors.append(f"{field} must be empty when the order has no items")
