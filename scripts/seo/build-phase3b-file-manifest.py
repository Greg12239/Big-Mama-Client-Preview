from __future__ import annotations

import json
from pathlib import Path

from _common import REPORTS_DIR, ROOT, atomic_write_json, sha256_file


PREFIXES = ("seo/", "scripts/seo/", "docs/seo/", "reports/seo/")
PHASE3B_DOCS = {
    "docs/seo/PRODUCTION-DECISION-FORM.md",
    "docs/seo/MULTI-ENGINE-SEARCH-STRATEGY.md",
    "docs/seo/LOCAL-SEARCH-OPERATIONS.md",
    "docs/seo/AEO-GEO-CONTENT-STANDARD.md",
    "docs/seo/SEARCH-MEASUREMENT-OPERATIONS.md",
    "docs/seo/DEPLOYMENT-AND-INDEXING-RUNBOOK.md",
}


def include(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return (
        rel.startswith(PREFIXES)
        and "/.cache/" not in f"/{rel}"
        and path.name != "phase3b-file-manifest.json"
        and ("phase3b" in path.name.lower() or rel in {
            "seo/production-truth.json", "seo/platform-coverage.json", "seo/url-policy.json", "seo/crawler-policy.json",
            "seo/entity-graph.json", "seo/local-search-source.json", "seo/answer-data.json", "seo/image-data.json",
            "seo/measurement-plan.json", "seo/review-operations.json", "seo/authority-plan.json",
        } or rel in PHASE3B_DOCS or rel == "reports/seo/PHASE-3B-FINAL-REPORT.md" or rel.startswith("reports/seo/generated-preview/phase3b/"))
    )


files = sorted((path for path in ROOT.rglob("*") if path.is_file() and include(path)), key=lambda p: p.relative_to(ROOT).as_posix())
records = [{"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size, "sha256": sha256_file(path)} for path in files]
payload = {"schemaVersion": "1.0.0", "phase": "3B", "recordCount": len(records), "aggregateBytes": sum(r["bytes"] for r in records), "records": records}
atomic_write_json(REPORTS_DIR / "phase3b-file-manifest.json", payload)
print(json.dumps({"records": len(records), "bytes": payload["aggregateBytes"]}, sort_keys=True))
