"""Command-line entry point for inspecting the project data foundation."""

import argparse
from pathlib import Path
from typing import Sequence

from .config import INPUT_DIR, POLICY_VERSION
from .data_repository import OlistRepository, load_case


def inspect_case(case_path: Path, repository: OlistRepository) -> None:
    case = load_case(case_path)
    if case.policy_version != POLICY_VERSION:
        raise ValueError(
            f"{case.case_id}: unsupported policy {case.policy_version!r}"
        )

    order = repository.get_order(case.claimed_order_id)
    if order is None:
        raise ValueError(
            f"{case.case_id}: order {case.claimed_order_id!r} was not found"
        )

    customer = repository.get_customer(order["customer_id"])
    items = repository.get_order_items(case.claimed_order_id)
    payments = repository.get_order_payments(case.claimed_order_id)

    print(f"case_id={case.case_id}")
    print(f"order_id={case.claimed_order_id}")
    print(f"order_status={order['order_status']}")
    print(f"customer_found={customer is not None}")
    print(f"item_rows={len(items)}")
    print(f"payment_rows={len(payments)}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--case",
        default="EC_001",
        help="Case ID to inspect without the .json suffix (default: EC_001)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repository = OlistRepository()
    inspect_case(INPUT_DIR / f"{args.case}.json", repository)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

