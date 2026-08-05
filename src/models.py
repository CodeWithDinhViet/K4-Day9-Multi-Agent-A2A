"""Typed contracts shared by the coordinator and domain agents."""

from dataclasses import dataclass
from typing import Any, Dict


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

