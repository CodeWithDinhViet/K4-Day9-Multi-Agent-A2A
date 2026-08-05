"""Deterministic implementation of EC_POLICY_V2."""

from decimal import Decimal
from typing import List

from ..models import InvestigationBundle, PolicyDecision, ResponsibleParty


ZERO = Decimal("0.00")


class PolicyAgent:
    """Classify a verified investigation bundle in policy priority order."""

    def decide(self, bundle: InvestigationBundle) -> PolicyDecision:
        order_status = bundle.order_product.order["order_status"]
        payment_total = bundle.payment.payment_total_brl
        freight_total = bundle.payment.freight_total_brl or ZERO

        if order_status == "canceled" and payment_total > ZERO:
            primary = "canceled_order_paid"
            cause = "ORDER_CANCELED_AFTER_PAYMENT"
            parties = [ResponsibleParty("platform", "OLIST_PLATFORM")]
            refund = payment_total
            primary_action = "issue_full_refund"
        elif order_status == "unavailable" and payment_total > ZERO:
            primary = "unavailable_order_paid"
            cause = "ORDER_UNAVAILABLE_AFTER_PAYMENT"
            parties = [ResponsibleParty("platform", "OLIST_PLATFORM")]
            refund = payment_total
            primary_action = "issue_full_refund"
        elif bundle.delivery.late_delivery and bundle.delivery.late_handoff_seller_ids:
            primary = "late_delivery_seller"
            cause = "SELLER_HANDOFF_AFTER_LIMIT"
            parties = [
                ResponsibleParty("seller", seller_id)
                for seller_id in bundle.delivery.late_handoff_seller_ids[:3]
            ]
            refund = freight_total
            primary_action = "refund_freight"
        elif bundle.delivery.late_delivery:
            primary = "late_delivery_logistics"
            cause = "CARRIER_DELIVERED_AFTER_ESTIMATE"
            parties = [
                ResponsibleParty("logistics_provider", "LOGISTICS_PROVIDER")
            ]
            refund = freight_total
            primary_action = "refund_freight"
        elif bundle.payment.split_payment and bundle.payment.reconciled is True:
            primary = "valid_split_payment"
            cause = "MULTIPLE_PAYMENTS_RECONCILED"
            parties = []
            refund = ZERO
            primary_action = "explain_valid_split_payment"
        elif (
            bundle.delivery.late_delivery is False
            and bundle.payment.reconciled is True
        ):
            primary = "unsupported_late_claim"
            cause = "DELIVERY_WITHIN_ESTIMATE"
            parties = []
            refund = ZERO
            primary_action = "reject_late_refund"
        else:
            raise ValueError(
                f"{bundle.case.case_id}: no EC_POLICY_V2 rule matched the case"
            )

        secondary = self._secondary_issues(bundle)
        actions = self._resolution_actions(bundle, primary, primary_action, refund)
        return PolicyDecision(
            primary_issue=primary,
            secondary_issues=secondary,
            case_status="action_required" if refund > ZERO else "no_action",
            root_cause_code=cause,
            responsible_parties=parties,
            recommended_refund_brl=refund,
            resolution_actions=actions[:5],
        )

    @staticmethod
    def _secondary_issues(bundle: InvestigationBundle) -> List[str]:
        issues = []
        if bundle.order_product.multi_item_order:
            issues.append("multi_item_order")
        if bundle.order_product.multi_seller_order:
            issues.append("multi_seller_order")
        if bundle.payment.split_payment:
            issues.append("split_payment")
        if bundle.customer.repeat_customer:
            issues.append("repeat_customer")
        if bundle.order_product.multiple_categories:
            issues.append("multiple_categories")
        return issues

    @staticmethod
    def _resolution_actions(
        bundle: InvestigationBundle,
        primary_issue: str,
        primary_action: str,
        refund: Decimal,
    ) -> List[str]:
        actions = [primary_action]
        if primary_issue == "late_delivery_seller":
            actions.append("review_seller_handoff")
        elif primary_issue == "late_delivery_logistics":
            actions.append("review_carrier_delay")
        if primary_issue in {"canceled_order_paid", "unavailable_order_paid"}:
            actions.append("verify_refund_completion")
        if bundle.order_product.multi_seller_order:
            actions.append("coordinate_multi_seller_case")
        if bundle.payment.split_payment and primary_issue != "valid_split_payment":
            actions.append("verify_payment_allocation")
        return actions
