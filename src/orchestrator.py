"""Coordinator that hands a case to each read-only domain agent."""

from .agents.customer_agent import CustomerAgent
from .agents.delivery_agent import DeliveryAgent
from .agents.order_product_agent import OrderProductAgent
from .agents.payment_agent import PaymentAgent
from .agents.policy_agent import PolicyAgent
from .agents.verifier_agent import VerifierAgent
from .data_repository import OlistRepository
from .models import CaseInput, InvestigationBundle


class InvestigationCoordinator:
    def __init__(self, repository: OlistRepository) -> None:
        self.customer_agent = CustomerAgent(repository)
        self.order_product_agent = OrderProductAgent(repository)
        self.payment_agent = PaymentAgent(repository)
        self.delivery_agent = DeliveryAgent(repository)
        self.policy_agent = PolicyAgent()
        self.verifier_agent = VerifierAgent(repository)

    def investigate(self, case: CaseInput) -> InvestigationBundle:
        order_id = case.claimed_order_id
        return InvestigationBundle(
            case=case,
            customer=self.customer_agent.investigate(order_id),
            order_product=self.order_product_agent.investigate(order_id),
            payment=self.payment_agent.investigate(order_id),
            delivery=self.delivery_agent.investigate(order_id),
        )

    def decide(self, bundle: InvestigationBundle):
        return self.policy_agent.decide(bundle)

    def verify(self, output, bundle, decision) -> None:
        self.verifier_agent.verify(output, bundle, decision)
