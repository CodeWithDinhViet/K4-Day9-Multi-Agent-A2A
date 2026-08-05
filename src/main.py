"""Command-line entry point for inspecting the project data foundation."""

import argparse
import json
from pathlib import Path
from typing import Sequence

from .config import INPUT_DIR, POLICY_VERSION
from .data_repository import OlistRepository, load_case
from .orchestrator import InvestigationCoordinator
from .output_builder import build_output
from .runner import run_all_cases, write_output


def inspect_case(
    case_path: Path,
    repository: OlistRepository,
    show_json: bool = False,
    write: bool = False,
) -> None:
    case = load_case(case_path)
    if case.policy_version != POLICY_VERSION:
        raise ValueError(
            f"{case.case_id}: unsupported policy {case.policy_version!r}"
        )

    coordinator = InvestigationCoordinator(repository)
    bundle = coordinator.investigate(case)
    decision = coordinator.decide(bundle)
    output = build_output(bundle, decision)
    coordinator.verify(output, bundle, decision)
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
    if show_json:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    if write:
        print(f"output_written={write_output(output)}")


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
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the selected case after successful verification",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Verify and write EC_001 through EC_050",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.all:
        destinations = run_all_cases()
        print(f"verified_outputs_written={len(destinations)}")
        return 0
    repository = OlistRepository()
    inspect_case(
        INPUT_DIR / f"{args.case}.json",
        repository,
        show_json=args.json,
        write=args.write,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
