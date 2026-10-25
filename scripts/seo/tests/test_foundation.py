from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from _common import BENCHMARK_TEMP_DIR, CACHE_DIR, DATA_DIR, REPORTS_DIR, ROOT, FoundationError, atomic_write_json, ensure_allowed_output, read_json, sha256_bytes, stable_json_bytes
from _foundation import FORBIDDEN_SCHEMA_TYPES, QUERY_METRIC_FIELDS, QUERY_REQUIRED_FIELDS, _schema_preview_payload, _walk_schema_types, _walk_schema_urls


class FoundationTests(unittest.TestCase):
    def test_cache_override_is_allowed(self) -> None:
        self.assertEqual(ensure_allowed_output(CACHE_DIR), CACHE_DIR.resolve())

    def test_root_cache_is_rejected(self) -> None:
        with self.assertRaises(FoundationError):
            ensure_allowed_output(ROOT / ".seo-cache" / "site-meta.json")

    def test_website_write_is_rejected(self) -> None:
        with self.assertRaises(FoundationError):
            ensure_allowed_output(ROOT / "public" / "seo.json")

    def test_stable_json_is_byte_deterministic(self) -> None:
        left = stable_json_bytes({"b": 2, "a": 1})
        right = stable_json_bytes({"a": 1, "b": 2})
        self.assertEqual(left, right)
        self.assertEqual(json.loads(left), {"a": 1, "b": 2})

    def test_atomic_write_skips_identical_bytes(self) -> None:
        path = BENCHMARK_TEMP_DIR / "unit-test.json"
        first = atomic_write_json(path, {"value": 1})
        second = atomic_write_json(path, {"value": 1})
        self.assertIn(first["status"], {"WRITTEN", "UNCHANGED"})
        self.assertEqual(second["status"], "UNCHANGED")
        path.unlink()
        if BENCHMARK_TEMP_DIR.exists() and not any(BENCHMARK_TEMP_DIR.iterdir()):
            BENCHMARK_TEMP_DIR.rmdir()

    def test_schema_preview_excludes_prohibited_types(self) -> None:
        detected = set(_walk_schema_types(_schema_preview_payload()["jsonLd"]))
        self.assertFalse(detected & FORBIDDEN_SCHEMA_TYPES)

    def test_schema_preview_omits_unresolved_public_urls(self) -> None:
        payload = _schema_preview_payload()
        self.assertEqual(_walk_schema_urls(payload["jsonLd"]), [])
        omitted = {row["type"] for row in payload["omittedEntities"]}
        self.assertTrue({"WebSite", "WebPage", "ImageObject"}.issubset(omitted))

    def test_query_contract_has_required_fields_and_null_metrics(self) -> None:
        queries = read_json(DATA_DIR / "query-universe.json")["queries"]
        for row in queries:
            self.assertFalse(QUERY_REQUIRED_FIELDS - set(row), row["id"])
            self.assertEqual(QUERY_METRIC_FIELDS & set(row), QUERY_METRIC_FIELDS, row["id"])
            self.assertTrue(all(row[field] is None for field in QUERY_METRIC_FIELDS), row["id"])

    def test_production_decisions_remain_setup_required(self) -> None:
        decisions = read_json(DATA_DIR / "production-decisions.json")
        self.assertIsNone(decisions["decisions"]["productionOrigin"]["value"])
        self.assertIsNone(decisions["decisions"]["socialImage"]["absoluteUrl"])
        self.assertFalse(decisions["deploymentReady"])

    def test_big_tokyo_remains_blocked(self) -> None:
        menu = read_json(DATA_DIR / "menu.json")
        big_tokyo = next(row for row in menu["products"] if row["id"] == "product:big-tokyo")
        self.assertEqual(big_tokyo["structuredDataEligibility"], "BLOCKED_CONTRADICTION")
        self.assertIsNone(big_tokyo["availability"])
        self.assertTrue(big_tokyo["contradictions"])

    def test_foundation_manifest_self_hash_is_verifiable(self) -> None:
        path = REPORTS_DIR / "foundation-file-manifest.json"
        manifest = read_json(path)
        self_row = next(row for row in manifest["files"] if row["relativePath"] == "reports/seo/foundation-file-manifest.json")
        expected = self_row["sha256"]
        self_row["sha256"] = "0" * 64
        self.assertEqual(sha256_bytes(stable_json_bytes(manifest)), expected)
        self.assertEqual(self_row["fileSize"], path.stat().st_size)


if __name__ == "__main__":
    unittest.main()
