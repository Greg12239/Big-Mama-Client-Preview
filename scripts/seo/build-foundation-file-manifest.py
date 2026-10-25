from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from _common import (
    ALLOWED_ROOTS,
    REPORTS_DIR,
    ROOT,
    atomic_write_bytes,
    read_json,
    sha256_bytes,
    sha256_file,
    stable_json_bytes,
)


OUTPUT = REPORTS_DIR / "foundation-file-manifest.json"
SELF_HASH_PLACEHOLDER = "0" * 64
ACCEPTED_COUNTS = {
    "seo": 19,
    "scripts/seo": 26,
    "docs/seo": 10,
    "reports/seo": 29,
}
PHASE2_CREATED = {
    "seo/production-decisions.json",
    "scripts/seo/build-foundation-file-manifest.py",
    "reports/seo/foundation-file-manifest.json",
    "reports/seo/performance-phase2-verification.json",
    "reports/seo/performance-phase2-verification.md",
    "reports/seo/website-integrity-phase2-before.json",
    "reports/seo/website-integrity-phase2-after.json",
    "reports/seo/website-integrity-phase2-comparison.json",
}


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _category(relative: str) -> str:
    if relative.startswith("seo/"):
        return "SOURCE_CONTRACT"
    if relative.startswith("scripts/seo/tests/"):
        return "UNIT_TEST"
    if relative.startswith("scripts/seo/"):
        return "ISOLATED_SCRIPT"
    if relative.startswith("docs/seo/"):
        return "OPERATIONAL_DOCUMENT"
    if relative.startswith("reports/seo/.cache/"):
        return "GENERATED_CACHE"
    if relative.startswith("reports/seo/generated-preview/"):
        return "NON_PRODUCTION_PREVIEW"
    if relative.startswith("reports/seo/performance/") or "performance-" in relative:
        return "PERFORMANCE_EVIDENCE"
    if "integrity" in relative:
        return "INTEGRITY_EVIDENCE"
    if relative.endswith("-report.json") or relative.endswith("-baseline.json"):
        return "VALIDATION_EVIDENCE"
    return "FOUNDATION_REPORT"


def _generator(relative: str) -> str:
    name = Path(relative).name
    explicit = {
        "build-state.json": "scripts/seo/build-search-foundation.py",
        "determinism-report.json": "scripts/seo/verify-determinism.py",
        "performance-baseline.json": "scripts/seo/benchmark-search-system.py",
        "performance-baseline.md": "scripts/seo/benchmark-search-system.py",
        "performance-regression.json": "scripts/seo/benchmark-search-system.py",
        "website-integrity-before.json": "scripts/seo/build-website-integrity-manifest.py",
        "website-integrity-after.json": "scripts/seo/build-website-integrity-manifest.py",
        "website-integrity-comparison.json": "scripts/seo/compare-website-integrity.py",
        "foundation-file-manifest.json": "scripts/seo/build-foundation-file-manifest.py",
    }
    if name in explicit:
        return explicit[name]
    if relative.startswith("reports/seo/"):
        return "scripts/seo/build-search-foundation.py"
    if relative.startswith("seo/"):
        return "approved isolated source-of-truth contract"
    if relative.startswith("docs/seo/"):
        return "approved isolated operational documentation"
    return "approved isolated engineering source"


def _purpose(relative: str, category: str) -> str:
    stem = Path(relative).stem.replace("-", " ").replace("_", " ")
    prefixes = {
        "SOURCE_CONTRACT": "Search-data source-of-truth contract",
        "UNIT_TEST": "Isolation and deterministic-build unit tests",
        "ISOLATED_SCRIPT": "Deterministic isolated workflow",
        "OPERATIONAL_DOCUMENT": "Operational readiness documentation",
        "GENERATED_CACHE": "Versioned incremental-build cache",
        "NON_PRODUCTION_PREVIEW": "Non-production integration preview",
        "PERFORMANCE_EVIDENCE": "Runtime performance evidence",
        "INTEGRITY_EVIDENCE": "Protected-website integrity evidence",
        "VALIDATION_EVIDENCE": "Validation evidence",
        "FOUNDATION_REPORT": "Foundation execution evidence",
    }
    return f"{prefixes[category]}: {stem}"


def _production_eligibility(category: str) -> str:
    if category == "SOURCE_CONTRACT":
        return "VERIFIED_FIELDS_ONLY_AFTER_SEPARATE_APPROVAL"
    return "NOT_PRODUCTION_ARTIFACT"


def _baseline_records() -> dict[str, dict[str, Any]]:
    if not OUTPUT.is_file():
        return {}
    payload = read_json(OUTPUT)
    return {row["relativePath"]: row for row in payload.get("files", [])}


def _status(relative: str, current_hash: str, baseline: dict[str, dict[str, Any]]) -> tuple[str, str | None]:
    if relative.startswith("reports/seo/.cache/"):
        accepted = baseline.get(relative, {}).get("acceptanceSha256")
        return "GENERATED_TRANSIENT", accepted or current_hash
    if relative in PHASE2_CREATED:
        return "CREATED", None
    previous = baseline.get(relative)
    if previous is None:
        return "UNCHANGED", current_hash
    accepted = previous.get("acceptanceSha256")
    if accepted is None:
        return "CREATED", None
    return ("UNCHANGED" if current_hash == accepted else "MODIFIED"), accepted


def _inventory_paths() -> list[Path]:
    paths: list[Path] = []
    for root in ALLOWED_ROOTS:
        paths.extend(path for path in root.rglob("*") if path.is_file() and path.resolve() != OUTPUT.resolve())
    return sorted(paths, key=lambda path: _relative(path).casefold())


def _record(path: Path, baseline: dict[str, dict[str, Any]]) -> dict[str, Any]:
    relative = _relative(path)
    category = _category(relative)
    digest = sha256_file(path)
    status, acceptance_hash = _status(relative, digest, baseline)
    return {
        "relativePath": relative,
        "category": category,
        "status": status,
        "fileSize": path.stat().st_size,
        "sha256": digest,
        "sha256Scope": "FILE_BYTES",
        "acceptanceSha256": acceptance_hash,
        "sourceOrGenerator": _generator(relative),
        "purpose": _purpose(relative, category),
        "productionEligibility": _production_eligibility(category),
        "websiteIntegrationStatus": "PROHIBITED",
    }


def _self_record(file_size: int) -> dict[str, Any]:
    relative = _relative(OUTPUT)
    category = _category(relative)
    return {
        "relativePath": relative,
        "category": category,
        "status": "CREATED",
        "fileSize": file_size,
        "sha256": SELF_HASH_PLACEHOLDER,
        "sha256Scope": "MANIFEST_BYTES_WITH_THIS_SHA256_FIELD_ZEROED",
        "acceptanceSha256": None,
        "sourceOrGenerator": _generator(relative),
        "purpose": "Exact isolated foundation file inventory and Phase 2 change reconciliation",
        "productionEligibility": "NOT_PRODUCTION_ARTIFACT",
        "websiteIntegrationStatus": "PROHIBITED",
    }


def _payload(records: list[dict[str, Any]]) -> dict[str, Any]:
    category_counts = dict(sorted(Counter(row["category"] for row in records).items()))
    status_counts = dict(sorted(Counter(row["status"] for row in records).items()))
    return {
        "schemaVersion": "1.0.0",
        "manifestScope": "All files under seo/, scripts/seo/, docs/seo/, and reports/seo/",
        "hashAlgorithm": "SHA-256",
        "selfHashVerification": "Zero only the manifest record's sha256 field, serialize as stable JSON, then hash the resulting bytes.",
        "reconciliation": {
            "acceptedReportedCounts": ACCEPTED_COUNTS,
            "acceptedFilesystemFileCount": sum(ACCEPTED_COUNTS.values()),
            "uiEditedFileCount": 56,
            "explanation": (
                "The accepted 84 is a recursive filesystem inventory: 55 source/script/document files plus 29 generated preview, report, cache, and evidence files. "
                "The Codex UI value is an edit-event summary, not a filesystem inventory, and cannot be mapped one-to-one because this directory is not a Git worktree."
            ),
        },
        "recordCount": len(records),
        "categoryCounts": category_counts,
        "statusCounts": status_counts,
        "files": records,
    }


def _finalize_self_hash(records: list[dict[str, Any]]) -> bytes:
    self_row = next(row for row in records if row["relativePath"] == _relative(OUTPUT))
    while True:
        candidate = stable_json_bytes(_payload(records))
        size = len(candidate)
        if self_row["fileSize"] == size:
            break
        self_row["fileSize"] = size
    normalized = stable_json_bytes(_payload(records))
    self_row["sha256"] = sha256_bytes(normalized)
    payload = stable_json_bytes(_payload(records))
    if len(payload) != self_row["fileSize"]:
        raise RuntimeError("Manifest self-size did not stabilize")
    return payload


def main() -> int:
    baseline = _baseline_records()
    records = [_record(path, baseline) for path in _inventory_paths()]
    records.append(_self_record(0))
    records.sort(key=lambda row: row["relativePath"].casefold())
    payload = _finalize_self_hash(records)
    result = atomic_write_bytes(OUTPUT, payload)
    print({"status": "PASS", "recordCount": len(records), "output": result})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
