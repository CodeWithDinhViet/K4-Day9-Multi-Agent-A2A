"""Verified single-case and batch execution utilities."""

import json
from pathlib import Path
from typing import Any, Dict, List

from .config import CASE_COUNT, INPUT_DIR, OUTPUT_DIR
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
    for number in range(1, CASE_COUNT + 1):
        case_path = input_dir / f"EC_{number:03d}.json"
        if not case_path.is_file():
            raise FileNotFoundError(f"Required input is missing: {case_path}")
        destinations.append(
            write_output(process_case(case_path, coordinator), output_dir)
        )
    return destinations
