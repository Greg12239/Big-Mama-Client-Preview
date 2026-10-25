from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable

from _common import DATA_DIR, REPORTS_DIR, ROOT, atomic_write_json, read_json
from _foundation import FORBIDDEN_SCHEMA_TYPES, QUERY_METRIC_FIELDS, QUERY_REQUIRED_FIELDS, _walk_schema_types


REQUIRED_ARTIFACTS = (
    "reports/seo/phase3-skill-routing.json",
    "reports/seo/phase3-agent-routing.json",
    "reports/seo/phase3-execution-manifest.json",
    "reports/seo/phase3-audit.json",
    "reports/seo/phase3-audit.md",
    "reports/seo/phase3-cross-review.json",
    "reports/seo/phase3-red-team.json",
    "reports/seo/phase3-issue-register.json",
    "reports/seo/phase3-test-matrix.json",
    "reports/seo/phase3-validation-report.json",
    "reports/seo/phase3-determinism-report.json",
    "reports/seo/phase3-file-manifest.json",
    "reports/seo/phase3-integration-plan.json",
    "reports/seo/phase3-integration-plan.md",
    "reports/seo/PHASE-3A-FINAL-REPORT.md",
    "reports/seo/performance/phase3/lab-results.json",
    "reports/seo/performance/phase3/benchmark.json",
    "reports/seo/website-integrity-phase3-after.json",
    "reports/seo/website-integrity-phase3-comparison.json",
)


def _safe_load(relative: str) -> dict[str, Any]:
    path = ROOT / relative
    return read_json(path) if path.is_file() else {}


def _check(identifier: str, category: str, description: str, predicate: Callable[[], bool], evidence: str) -> dict[str, Any]:
    try:
        passed = bool(predicate())
        error = None
    except Exception as exc:  # Validation must report all failures in one pass.
        passed = False
        error = f"{type(exc).__name__}: {exc}"
    return {
        "id": identifier,
        "category": category,
        "description": description,
        "status": "PASS" if passed else "FAIL",
        "evidence": evidence,
        "error": error,
    }


def run_checks(require_complete: bool) -> list[dict[str, Any]]:
    routing = _safe_load("reports/seo/phase3-skill-routing.json")
    agents = _safe_load("reports/seo/phase3-agent-routing.json")
    audit = _safe_load("reports/seo/phase3-audit.json")
    issues = _safe_load("reports/seo/phase3-issue-register.json")
    cross = _safe_load("reports/seo/phase3-cross-review.json")
    red = _safe_load("reports/seo/phase3-red-team.json")
    plan = _safe_load("reports/seo/phase3-integration-plan.json")
    execution = _safe_load("reports/seo/phase3-execution-manifest.json")
    schema = _safe_load("reports/seo/generated-preview/phase3/schema-preview.json")
    hreflang = _safe_load("reports/seo/generated-preview/phase3/hreflang-preview.json")
    answers = _safe_load("reports/seo/generated-preview/phase3/answer-preview.json")
    menu = read_json(DATA_DIR / "menu.json")
    queries = read_json(DATA_DIR / "query-universe.json")["queries"]
    decisions = read_json(DATA_DIR / "production-decisions.json")
    competitors = read_json(DATA_DIR / "competitor-baseline.json")
    local_pack = read_json(DATA_DIR / "local-pack-baseline.json")
    backlinks = read_json(DATA_DIR / "backlinks.json")
    citations = read_json(DATA_DIR / "citations.json")
    crawler = read_json(DATA_DIR / "crawler-policy.json")
    phase2_manifest = read_json(REPORTS_DIR / "foundation-file-manifest.json")
    before = _safe_load("reports/seo/website-integrity-phase3-before.json")
    after = _safe_load("reports/seo/website-integrity-phase3-after.json")
    comparison = _safe_load("reports/seo/website-integrity-phase3-comparison.json")
    lab = _safe_load("reports/seo/performance/phase3/lab-results.json")
    benchmark = _safe_load("reports/seo/performance/phase3/benchmark.json")
    determinism = _safe_load("reports/seo/phase3-determinism-report.json")
    manifest = _safe_load("reports/seo/phase3-file-manifest.json")

    big_tokyo = next(row for row in menu["products"] if row["id"] == "product:big-tokyo")
    schema_types = set(_walk_schema_types(schema.get("jsonLd", {})))
    priorities = {row.get("priority") for row in issues.get("issues", [])}
    records = [
        _check("T01", "isolation", "Approved output roots are documented", lambda: execution.get("cachePath") == "reports/seo/.cache/", "phase3-execution-manifest.json"),
        _check("T02", "isolation", "Root .seo-cache is absent", lambda: not (ROOT / ".seo-cache").exists(), ".seo-cache"),
        _check("T03", "isolation", "Website integration remains blocked", lambda: plan.get("websiteIntegrationStatus") == "BLOCKED", "phase3-integration-plan.json"),
        _check("T04", "baseline", "Accepted Phase 2 manifest remains present", lambda: (REPORTS_DIR / "foundation-file-manifest.json").is_file(), "foundation-file-manifest.json"),
        _check("T05", "baseline", "Accepted Phase 2 inventory contains 120 files", lambda: phase2_manifest.get("recordCount") == 120, "foundation-file-manifest.json"),
        _check("T06", "integrity", "Phase 3 before manifest contains 44 protected files", lambda: before.get("protected_file_count") == 44, "website-integrity-phase3-before.json"),
        _check("T07", "integrity", "Protected file count is unchanged", lambda: after.get("protected_file_count") == before.get("protected_file_count") == 44, "phase3 before/after integrity"),
        _check("T08", "integrity", "Protected bytes are unchanged", lambda: comparison.get("beforeAggregateBytes") == comparison.get("afterAggregateBytes"), "website-integrity-phase3-comparison.json"),
        _check("T09", "integrity", "Protected SHA-256 comparison passes", lambda: comparison.get("status") == "PASS" and comparison.get("protectedFilesUnchanged") is True, "website-integrity-phase3-comparison.json"),
        _check("T10", "source", "Exactly one H1 is present", lambda: audit.get("evidence", {}).get("structure", {}).get("h1Count") == 1, "phase3-audit.json"),
        _check("T11", "source", "Heading hierarchy has no level skips", lambda: audit.get("evidence", {}).get("structure", {}).get("headingSkips") == [], "phase3-audit.json"),
        _check("T12", "source", "Image alt attributes are present", lambda: audit.get("evidence", {}).get("images", {}).get("missingAltCount") == 0, "phase3-audit.json"),
        _check("T13", "source", "Image dimensions are present", lambda: audit.get("evidence", {}).get("images", {}).get("missingDimensionCount") == 0, "phase3-audit.json"),
        _check("T14", "source", "Canonical absence is recorded, not concealed", lambda: audit.get("evidence", {}).get("metadata", {}).get("canonicalCount") == 0, "phase3-audit.json"),
        _check("T15", "source", "JSON-LD absence is recorded, not concealed", lambda: audit.get("evidence", {}).get("metadata", {}).get("jsonLdCount") == 0, "phase3-audit.json"),
        _check("T16", "source", "Open Graph absence is recorded", lambda: audit.get("evidence", {}).get("metadata", {}).get("openGraphCount") == 0, "phase3-audit.json"),
        _check("T17", "source", "Twitter metadata absence is recorded", lambda: audit.get("evidence", {}).get("metadata", {}).get("twitterCount") == 0, "phase3-audit.json"),
        _check("T18", "trust", "Placeholder email is explicitly flagged", lambda: audit.get("evidence", {}).get("trustAndLocal", {}).get("placeholderEmailObserved") is True, "phase3-audit.json"),
        _check("T19", "trust", "Displayed rating is explicitly flagged", lambda: audit.get("evidence", {}).get("trustAndLocal", {}).get("displayedRatingObserved") is True, "phase3-audit.json"),
        _check("T20", "schema", "Big Tokyo remains blocked from schema", lambda: big_tokyo.get("structuredDataEligibility") == "BLOCKED_CONTRADICTION", "seo/menu.json"),
        _check("T21", "readiness", "Production origin remains unresolved", lambda: decisions["decisions"]["productionOrigin"]["value"] is None, "seo/production-decisions.json"),
        _check("T22", "readiness", "Social image remains unresolved", lambda: decisions["decisions"]["socialImage"]["absoluteUrl"] is None, "seo/production-decisions.json"),
        _check("T23", "queries", "All query records contain required fields", lambda: all(not (QUERY_REQUIRED_FIELDS - set(row)) for row in queries), "seo/query-universe.json"),
        _check("T24", "queries", "Unsupported live query metrics remain null", lambda: all(all(row[field] is None for field in QUERY_METRIC_FIELDS) for row in queries), "seo/query-universe.json"),
        _check("T25", "competitors", "Competitor observations remain empty without network evidence", lambda: competitors.get("observations") == [], "seo/competitor-baseline.json"),
        _check("T26", "local", "Local Pack observations remain empty without network evidence", lambda: local_pack.get("observations") == [], "seo/local-pack-baseline.json"),
        _check("T27", "backlinks", "Backlink metrics remain insufficient/unavailable", lambda: backlinks.get("links") == [] and all(value is None for value in backlinks.get("metrics", {}).values()), "seo/backlinks.json"),
        _check("T28", "citations", "Citation external verification remains unavailable", lambda: citations.get("externalVerificationStatus") not in {"VERIFIED", "COMPLETE"}, "seo/citations.json"),
        _check("T29", "crawlers", "Crawler policy remains preview-only", lambda: crawler.get("previewOnly") is True, "seo/crawler-policy.json"),
        _check("T30", "schema", "Schema preview excludes prohibited types", lambda: not (schema_types & FORBIDDEN_SCHEMA_TYPES), "schema-preview.json"),
        _check("T31", "schema", "Schema preview excludes Big Tokyo", lambda: "Big Tokyo" not in json.dumps(schema, ensure_ascii=False), "schema-preview.json"),
        _check("T32", "sitemap", "Sitemap preview contains no placeholder production origin", lambda: "example.com" not in (ROOT / "reports/seo/generated-preview/phase3/sitemap-preview.xml").read_text(encoding="utf-8"), "sitemap-preview.xml"),
        _check("T33", "robots", "Robots preview contains no placeholder production origin", lambda: "example.com" not in (ROOT / "reports/seo/generated-preview/phase3/robots-preview.txt").read_text(encoding="utf-8"), "robots-preview.txt"),
        _check("T34", "hreflang", "Hreflang is deferred pending language strategy", lambda: hreflang.get("status") == "DEFERRED_USER_DECISION_REQUIRED", "hreflang-preview.json"),
        _check("T35", "aeo", "Hidden AEO content is prohibited", lambda: answers.get("hiddenAeoContentAllowed") is False and answers.get("visibleContentRequired") is True, "answer-preview.json"),
        _check("T36", "routing", "All 26 specialist skills are routed", lambda: routing.get("installedSpecialistCount") == 26 and len(routing.get("specialists", [])) == 26, "phase3-skill-routing.json"),
        _check("T37", "routing", "All 24 installed agent profiles are inventoried", lambda: agents.get("installedProfileCount") == 24, "phase3-agent-routing.json"),
        _check("T38", "routing", "Only audit and page are profileless", lambda: set(agents.get("profilelessSpecialists", [])) == {"seo-audit", "seo-page"}, "phase3-agent-routing.json"),
        _check("T39", "issues", "Issue priorities use P0-P3 only", lambda: priorities <= {"P0", "P1", "P2", "P3"}, "phase3-issue-register.json"),
        _check("T40", "issues", "No unsupported P0 issue is claimed", lambda: issues.get("counts", {}).get("P0") == 0, "phase3-issue-register.json"),
        _check("T41", "cross-review", "Cross-review completed with gated decisions", lambda: cross.get("status") == "PASS_WITH_GATED_DECISIONS", "phase3-cross-review.json"),
        _check("T42", "red-team", "Red-team controls pass", lambda: red.get("status") == "PASS", "phase3-red-team.json"),
        _check("T43", "network", "External network allowance is zero", lambda: execution.get("externalNetworkRequestsAllowed") == 0 and lab.get("network", {}).get("externalAllowed") == 0, "execution manifest and lab results"),
        _check("T44", "browser", "Browser budget is at most one launch and two pages", lambda: lab.get("browser", {}).get("launches", 0) <= 1 and lab.get("browser", {}).get("pages", 0) <= 2, "lab-results.json"),
        _check("T45", "determinism", "Semantic rebuild is deterministic", lambda: determinism.get("status") == "PASS" and determinism.get("changedOutputs") == [], "phase3-determinism-report.json"),
        _check("T46", "performance", "Phase 3 benchmark passes without replacing Phase 2", lambda: (not require_complete) or (benchmark.get("status") == "PASS" and benchmark.get("acceptedPhase2BaselinePreserved") is True), "performance/phase3/benchmark.json"),
    ]
    if require_complete:
        missing = [path for path in REQUIRED_ARTIFACTS if not (ROOT / path).is_file()]
        records.append({"id": "T47", "category": "artifacts", "description": "All required Phase 3A artifacts exist", "status": "PASS" if not missing else "FAIL", "evidence": "all required artifacts present" if not missing else ", ".join(missing), "error": None})
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate isolated Phase 3A outputs")
    parser.add_argument("--core-only", action="store_true", help="Run checks without requiring or writing final artifacts")
    args = parser.parse_args()
    checks = run_checks(require_complete=not args.core_only)
    failed = [row for row in checks if row["status"] == "FAIL"]
    result = {"status": "PASS" if not failed else "FAIL", "passed": len(checks) - len(failed), "failed": len(failed)}
    if not args.core_only:
        matrix = {
            "schemaVersion": "1.0.0",
            "status": result["status"],
            "testCount": len(checks),
            "passed": result["passed"],
            "failed": result["failed"],
            "setupRequiredIsNotFailure": True,
            "tests": checks,
        }
        atomic_write_json(REPORTS_DIR / "phase3-test-matrix.json", matrix)
        report = {
            "schemaVersion": "1.0.0",
            "status": result["status"],
            "tests": {"passed": result["passed"], "failed": result["failed"], "total": len(checks)},
            "failedTests": failed,
            "productionReady": False,
            "blueprintReady": not failed,
            "websiteIntegrationStatus": "BLOCKED",
            "requiredApproval": "APPROVED — ALLOW SEO INTEGRATION INTO WEBSITE",
        }
        atomic_write_json(REPORTS_DIR / "phase3-validation-report.json", report)
    print(json.dumps(result, sort_keys=True))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
