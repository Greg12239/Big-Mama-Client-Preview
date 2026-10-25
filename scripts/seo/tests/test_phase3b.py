from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from _common import DATA_DIR, REPORTS_DIR, ROOT, read_json  # noqa: E402
from _phase3b import INTEGRATION_APPROVAL, TEST_NAMES, validate_phase3b  # noqa: E402


class Phase3BTests(unittest.TestCase):
    def test_matrix_has_63_domains(self) -> None:
        self.assertEqual(63, len(TEST_NAMES))

    def test_truth_has_44_fields(self) -> None:
        truth = read_json(DATA_DIR / "production-truth.json")
        self.assertEqual(44, truth["fieldCount"])
        self.assertGreater(truth["unresolvedCount"], 0)

    def test_website_integration_is_blocked(self) -> None:
        plan = read_json(REPORTS_DIR / "phase3b-search-activation-plan.json")
        self.assertEqual("BLOCKED", plan["websiteIntegrationStatus"])
        self.assertEqual(INTEGRATION_APPROVAL, plan["requiredApprovals"]["websiteIntegration"])

    def test_no_root_cache(self) -> None:
        self.assertFalse((ROOT / ".seo-cache").exists())

    def test_big_tokyo_is_blocked(self) -> None:
        graph = read_json(DATA_DIR / "entity-graph.json")
        self.assertIn("product:big-tokyo", graph["nodes"][3]["blockedProductIds"])

    def test_no_external_activity(self) -> None:
        execution = read_json(REPORTS_DIR / "phase3b-execution-manifest.json")
        self.assertEqual(0, execution["externalAccountsAccessed"])
        self.assertEqual(0, execution["browserLaunches"])

    def test_validation_guardrails_pass(self) -> None:
        report = validate_phase3b()
        self.assertEqual("PASS", report["status"])
        self.assertEqual(63, report["tests"]["passed"])


if __name__ == "__main__":
    unittest.main()
