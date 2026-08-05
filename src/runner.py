"""Verified single-case and batch execution utilities."""

import json
import platform
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from .config import (
    CASE_COUNT,
    INPUT_DIR,
    LOGGING_DIR,
    MODEL_NAME,
    MODEL_PARAMETER_SIZE,
    OUTPUT_DIR,
    POLICY_VERSION,
)
from .data_repository import OlistRepository, load_case
from .orchestrator import InvestigationCoordinator
from .output_builder import build_output


def process_case(
    case_path: Path, coordinator: InvestigationCoordinator
) -> Dict[str, Any]:
    case = load_case(case_path)
    bundle = coordinator.investigate(case)
    decision = coordinator.decide(bundle)
    output = build_output(bundle, decision)
    coordinator.verify(output, bundle, decision)
    return output


def write_output(output: Dict[str, Any], output_dir: Path = OUTPUT_DIR) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / f"{output['case_id']}.json"
    temporary = destination.with_suffix(".json.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    temporary.replace(destination)
    return destination


def run_all_cases(
    input_dir: Path = INPUT_DIR, output_dir: Path = OUTPUT_DIR
) -> List[Path]:
    repository = OlistRepository()
    coordinator = InvestigationCoordinator(repository)
    destinations = []
    trace_events = []
    for number in range(1, CASE_COUNT + 1):
        case_path = input_dir / f"EC_{number:03d}.json"
        if not case_path.is_file():
            raise FileNotFoundError(f"Required input is missing: {case_path}")
        case = load_case(case_path)
        bundle = coordinator.investigate(case)
        decision = coordinator.decide(bundle)
        output = build_output(bundle, decision)
        coordinator.verify(output, bundle, decision)
        destination = write_output(output, output_dir)
        destinations.append(destination)
        trace_events.extend(_case_trace(bundle, decision, output, destination))
    _write_run_artifacts(trace_events)
    return destinations


def _case_trace(
    bundle, decision, output: Dict[str, Any], destination: Path
) -> List[Dict[str, Any]]:
    case_id = bundle.case.case_id
    order_id = bundle.case.claimed_order_id
    return [
        {
            "case_id": case_id,
            "agent": "coordinator",
            "event": "case_received",
            "order_id": order_id,
            "policy_version": bundle.case.policy_version,
        },
        {
            "case_id": case_id,
            "agent": "customer_agent",
            "event": "handoff_completed",
            "customer_unique_id": bundle.customer.customer_unique_id,
            "related_order_count": len(bundle.customer.related_order_ids),
        },
        {
            "case_id": case_id,
            "agent": "order_product_agent",
            "event": "handoff_completed",
            "item_count": len(bundle.order_product.item_rows),
            "seller_count": len(bundle.order_product.seller_ids),
            "product_count": len(bundle.order_product.product_ids),
        },
        {
            "case_id": case_id,
            "agent": "payment_agent",
            "event": "handoff_completed",
            "payment_count": len(bundle.payment.payment_rows),
            "payment_total_brl": float(bundle.payment.payment_total_brl),
            "reconciled": bundle.payment.reconciled,
        },
        {
            "case_id": case_id,
            "agent": "delivery_agent",
            "event": "handoff_completed",
            "delivery_variance_hours": (
                float(bundle.delivery.delivery_variance_hours)
                if bundle.delivery.delivery_variance_hours is not None
                else None
            ),
            "late_handoff_seller_count": len(
                bundle.delivery.late_handoff_seller_ids
            ),
        },
        {
            "case_id": case_id,
            "agent": "policy_agent",
            "event": "decision_completed",
            "primary_issue": decision.primary_issue,
            "root_cause_code": decision.root_cause_code,
            "recommended_refund_brl": float(
                decision.recommended_refund_brl
            ),
        },
        {
            "case_id": case_id,
            "agent": "verifier_agent",
            "event": "verification_passed",
            "evidence_count": len(output["evidence_ids"]),
        },
        {
            "case_id": case_id,
            "agent": "coordinator",
            "event": "output_written",
            "path": destination.as_posix(),
        },
    ]


def _write_run_artifacts(events: List[Dict[str, Any]]) -> None:
    LOGGING_DIR.mkdir(parents=True, exist_ok=True)
    trace_path = LOGGING_DIR / "trace.jsonl"
    trace_temporary = trace_path.with_suffix(".jsonl.tmp")
    with trace_temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for event in events:
            handle.write(json.dumps(event, ensure_ascii=False, allow_nan=False))
            handle.write("\n")
    trace_temporary.replace(trace_path)

    metadata = {
        "model": MODEL_NAME,
        "parameter_size": MODEL_PARAMETER_SIZE,
        "framework": "custom Python multi-agent orchestration",
        "runtime": f"Python {platform.python_version()}",
        "policy_version": POLICY_VERSION,
        "case_count": CASE_COUNT,
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    metadata_path = LOGGING_DIR / "metadata.json"
    metadata_temporary = metadata_path.with_suffix(".json.tmp")
    with metadata_temporary.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    metadata_temporary.replace(metadata_path)
