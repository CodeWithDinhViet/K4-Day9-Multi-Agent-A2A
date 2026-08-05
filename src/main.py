"""Command-line entry point for inspecting the project data foundation."""

import argparse
import json
from pathlib import Path
from typing import Sequence

from .config import INPUT_DIR, POLICY_VERSION
from .data_repository import OlistRepository, load_case
from .orchestrator import InvestigationCoordinator
from .output_builder import build_output


def inspect_case(case_path: Path, repository: OlistRepository) -> None:
    case = load_case(case_path)
    if case.policy_version != POLICY_VERSION:
        raise ValueError(
            f"{case.case_id}: unsupported policy {case.policy_version!r}"
        )

    coordinator = InvestigationCoordinator(repository)
    bundle = coordinator.investigate(case)
    decision = coordinator.decide(bundle)
    output = build_output(bundle, decision)
    order = bundle.order_product.order

    print(f"case_id={case.case_id}")
    print(f"order_id={case.claimed_order_id}")
    print(f"order_status={order['order_status']}")
    print(f"customer_unique_id={bundle.customer.customer_unique_id}")
    print(f"related_orders={len(bundle.customer.related_order_ids)}")
    print(f"item_rows={len(bundle.order_product.item_rows)}")
    print(f"seller_count={len(bundle.order_product.seller_ids)}")
    print(f"payment_rows={len(bundle.payment.payment_rows)}")
    print(f"payment_total_brl={bundle.payment.payment_total_brl}")
    print(f"reconciled={bundle.payment.reconciled}")
    print(f"delivery_variance_hours={bundle.delivery.delivery_variance_hours}")
    print(f"late_handoff_sellers={len(bundle.delivery.late_handoff_seller_ids)}")
    print(f"primary_issue={decision.primary_issue}")
    print(f"secondary_issues={','.join(decision.secondary_issues)}")
    print(f"responsible_parties={len(decision.responsible_parties)}")
    print(f"recommended_refund_brl={decision.recommended_refund_brl}")
    print(f"resolution_actions={','.join(decision.resolution_actions)}")
    if args.json:
        print(json.dumps(output, ensure_ascii=False, indent=2))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        default="EC_001",
        help="Case ID to inspect without the .json suffix (default: EC_001)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the complete submission-shaped JSON after the summary",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repository = OlistRepository()
    inspect_case(INPUT_DIR / f"{args.case}.json", repository)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
