from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]
ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _common import CACHE_DIR, REPORTS_DIR, FoundationError, ensure_allowed_output, read_json, stable_json_bytes
from _foundation import FORBIDDEN_SCHEMA_TYPES, _walk_schema_types
from _phase3 import INTEGRATION_APPROVAL, SEMANTIC_OUTPUTS, SKILLS


class Phase3Tests(unittest.TestCase):
    def test_all_specialists_are_declared_once(self) -> None:
        names = [row["name"] for row in SKILLS]
        self.assertEqual(len(names), 26)
        self.assertEqual(len(set(names)), 26)

    def test_all_specialist_skill_files_exist(self) -> None:
        routing = read_json(REPORTS_DIR / "phase3-skill-routing.json")
        self.assertTrue(all(row["skillExists"] for row in routing["specialists"]))

    def test_agent_profile_inventory_is_exact(self) -> None:
        routing = read_json(REPORTS_DIR / "phase3-agent-routing.json")
        self.assertEqual(routing["installedProfileCount"], 24)
        self.assertEqual(set(routing["profilelessSpecialists"]), {"seo-audit", "seo-page"})

    def test_semantic_outputs_exist(self) -> None:
        self.assertTrue(all((ROOT / path).is_file() for path in SEMANTIC_OUTPUTS))

    def test_semantic_json_is_canonical(self) -> None:
        for relative in SEMANTIC_OUTPUTS:
            path = ROOT / relative
            if path.suffix != ".json":
                continue
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(path.read_bytes(), stable_json_bytes(payload), relative)

    def test_phase3_cache_override_is_allowed(self) -> None:
        self.assertEqual(ensure_allowed_output(CACHE_DIR), CACHE_DIR.resolve())

    def test_root_cache_is_forbidden(self) -> None:
        with self.assertRaises(FoundationError):
            ensure_allowed_output(ROOT / ".seo-cache" / "phase3.json")

    def test_website_output_is_forbidden(self) -> None:
        with self.assertRaises(FoundationError):
            ensure_allowed_output(ROOT / "index.html")

    def test_schema_preview_excludes_prohibited_types(self) -> None:
        payload = read_json(REPORTS_DIR / "generated-preview" / "phase3" / "schema-preview.json")
        self.assertFalse(set(_walk_schema_types(payload["jsonLd"])) & FORBIDDEN_SCHEMA_TYPES)

    def test_schema_preview_excludes_big_tokyo(self) -> None:
        payload = read_json(REPORTS_DIR / "generated-preview" / "phase3" / "schema-preview.json")
        self.assertNotIn("Big Tokyo", json.dumps(payload, ensure_ascii=False))

    def test_previews_omit_placeholder_origins(self) -> None:
        preview = REPORTS_DIR / "generated-preview" / "phase3"
        for name in ("metadata-preview.html", "sitemap-preview.xml", "robots-preview.txt", "schema-preview.json"):
            self.assertNotIn("example.com", (preview / name).read_text(encoding="utf-8"), name)

    def test_hreflang_is_gated(self) -> None:
        payload = read_json(REPORTS_DIR / "generated-preview" / "phase3" / "hreflang-preview.json")
        self.assertEqual(payload["status"], "DEFERRED_USER_DECISION_REQUIRED")

    def test_answer_preview_requires_visible_content(self) -> None:
        payload = read_json(REPORTS_DIR / "generated-preview" / "phase3" / "answer-preview.json")
        self.assertTrue(payload["visibleContentRequired"])
        self.assertFalse(payload["hiddenAeoContentAllowed"])

    def test_issue_register_has_no_p0(self) -> None:
        payload = read_json(REPORTS_DIR / "phase3-issue-register.json")
        self.assertEqual(payload["counts"]["P0"], 0)
        self.assertTrue(payload["issues"])

    def test_cross_review_is_complete(self) -> None:
        payload = read_json(REPORTS_DIR / "phase3-cross-review.json")
        self.assertEqual(payload["status"], "PASS_WITH_GATED_DECISIONS")

    def test_red_team_is_complete(self) -> None:
        payload = read_json(REPORTS_DIR / "phase3-red-team.json")
        self.assertEqual(payload["status"], "PASS")
        self.assertTrue(all(row["result"].startswith("PASS") for row in payload["attacks"]))

    def test_integration_plan_requires_exact_gate(self) -> None:
        payload = read_json(REPORTS_DIR / "phase3-integration-plan.json")
        self.assertEqual(payload["approvalRequired"], INTEGRATION_APPROVAL)
        self.assertEqual(payload["websiteIntegrationStatus"], "BLOCKED")

    def test_execution_manifest_forbids_external_network(self) -> None:
        payload = read_json(REPORTS_DIR / "phase3-execution-manifest.json")
        self.assertEqual(payload["externalNetworkRequestsAllowed"], 0)
        self.assertEqual(payload["externalAccountActivity"], 0)

    def test_accepted_phase2_manifest_remains_120(self) -> None:
        payload = read_json(REPORTS_DIR / "foundation-file-manifest.json")
        self.assertEqual(payload["recordCount"], 120)

    def test_source_audit_reports_no_website_write(self) -> None:
        payload = read_json(REPORTS_DIR / "phase3-audit.json")
        self.assertFalse(payload["websiteModified"])
        self.assertEqual(payload["websiteIntegrationStatus"], "BLOCKED")


if __name__ == "__main__":
    unittest.main()
