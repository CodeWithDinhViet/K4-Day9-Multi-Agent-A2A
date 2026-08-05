import json
import unittest
from collections import Counter
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

from src.agents.verifier_agent import VerificationError
from src.config import INPUT_DIR, OUTPUT_DIR
from src.data_repository import OlistRepository, load_case
from src.orchestrator import InvestigationCoordinator
from src.output_builder import build_output


class PipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repository = OlistRepository()
        cls.coordinator = InvestigationCoordinator(cls.repository)
        cls.results = []
        for path in sorted(INPUT_DIR.glob("EC_*.json")):
            bundle = cls.coordinator.investigate(load_case(path))
            decision = cls.coordinator.decide(bundle)
            output = build_output(bundle, decision)
            cls.results.append((path, bundle, decision, output))

    def test_all_fifty_cases_are_loaded(self) -> None:
        self.assertEqual(len(self.results), 50)
        self.assertEqual(
            [row[0].name for row in self.results],
            [f"EC_{number:03d}.json" for number in range(1, 51)],
        )

    def test_all_policy_branches_are_covered(self) -> None:
        counts = Counter(row[2].primary_issue for row in self.results)
        self.assertEqual(
            counts,
            {
                "canceled_order_paid": 8,
                "unavailable_order_paid": 6,
                "late_delivery_seller": 10,
                "late_delivery_logistics": 10,
                "valid_split_payment": 8,
                "unsupported_late_claim": 8,
            },
        )

    def test_payment_formula_and_null_handling(self) -> None:
        for _, bundle, _, output in self.results:
            payment = output["payment_reconciliation"]
            if not bundle.order_product.item_rows:
                for field in (
                    "expected_total_brl",
                    "difference_brl",
                    "reconciled",
                ):
                    self.assertIsNone(payment[field])
                self.assertEqual(payment["item_total_brl"], 0.0)
                self.assertEqual(payment["freight_total_brl"], 0.0)
                continue
            expected = Decimal(str(payment["item_total_brl"])) + Decimal(
                str(payment["freight_total_brl"])
            )
            difference = Decimal(str(payment["payment_total_brl"])) - expected
            self.assertEqual(Decimal(str(payment["expected_total_brl"])), expected)
            self.assertEqual(Decimal(str(payment["difference_brl"])), difference)
            self.assertEqual(payment["reconciled"], abs(difference) <= Decimal("0.10"))

    def test_every_built_output_passes_verifier(self) -> None:
        for _, bundle, decision, output in self.results:
            self.coordinator.verify(output, bundle, decision)

    def test_fake_evidence_is_rejected(self) -> None:
        _, bundle, decision, output = self.results[0]
        invalid = deepcopy(output)
        invalid["evidence_ids"].append("seller:not-a-real-seller")
        with self.assertRaises(VerificationError):
            self.coordinator.verify(invalid, bundle, decision)

    def test_checked_in_outputs_are_reproducible(self) -> None:
        for path, _, _, expected in self.results:
            output_path = OUTPUT_DIR / path.name
            with output_path.open(encoding="utf-8") as handle:
                actual = json.load(handle)
            self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
