from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from _common import ALLOWED_ROOTS, REPORTS_DIR, ROOT, atomic_write_bytes, read_json, sha256_bytes, sha256_file, stable_json_bytes


OUTPUT = REPORTS_DIR / "phase3-file-manifest.json"
PHASE2 = REPORTS_DIR / "foundation-file-manifest.json"
ZERO_HASH = "0" * 64


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _category(relative: str) -> str:
    if relative.startswith("reports/seo/.cache/"):
        return "GENERATED_TRANSIENT"
    if relative.startswith("seo/"):
        return "SOURCE_CONTRACT"
    if relative.startswith("scripts/seo/tests/"):
        return "UNIT_TEST"
    if relative.startswith("scripts/seo/"):
        return "ISOLATED_SCRIPT"
    if relative.startswith("docs/seo/"):
        return "OPERATIONAL_DOCUMENT"
    if relative.startswith("reports/seo/generated-preview/phase3/"):
        return "PHASE3_PREVIEW"
    if relative.startswith("reports/seo/performance/phase3/"):
        return "PHASE3_PERFORMANCE_EVIDENCE"
    if "integrity-phase3" in relative:
        return "PHASE3_INTEGRITY_EVIDENCE"
    if "phase3" in relative.casefold() or "PHASE-3A" in relative:
        return "PHASE3_EVIDENCE"
    return "ACCEPTED_FOUNDATION_FILE"


def _baseline() -> dict[str, dict[str, Any]]:
    payload = read_json(PHASE2)
    return {row["relativePath"]: row for row in payload["files"]}


def _records() -> list[dict[str, Any]]:
    baseline = _baseline()
    paths: list[Path] = []
    for root in ALLOWED_ROOTS:
        paths.extend(path for path in root.rglob("*") if path.is_file() and path.resolve() != OUTPUT.resolve())
    rows = []
    for path in sorted(paths, key=lambda item: _relative(item).casefold()):
        relative = _relative(path)
        digest = sha256_file(path)
        accepted = baseline.get(relative)
        category = _category(relative)
        if category == "GENERATED_TRANSIENT":
            status = "GENERATED_TRANSIENT"
        elif accepted is None:
            status = "CREATED"
        else:
            accepted_hash = accepted.get("sha256")
            if accepted.get("sha256Scope") == "MANIFEST_BYTES_WITH_THIS_SHA256_FIELD_ZEROED":
                accepted_payload = read_json(path)
                accepted_self = next(row for row in accepted_payload["files"] if row["relativePath"] == relative)
                accepted_self["sha256"] = ZERO_HASH
                current_matches = sha256_bytes(stable_json_bytes(accepted_payload)) == accepted_hash
            else:
                current_matches = accepted_hash == digest
            status = "UNCHANGED" if current_matches else "MODIFIED"
        rows.append({
            "relativePath": relative,
            "category": category,
            "status": status,
            "fileSize": path.stat().st_size,
            "sha256": digest,
            "acceptedPhase2Sha256": accepted.get("sha256") if accepted else None,
            "websiteIntegrationStatus": "PROHIBITED",
        })
    return rows


def _payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schemaVersion": "1.0.0",
        "scope": "All files under seo/, scripts/seo/, docs/seo/, and reports/seo/ after Phase 3A",
        "hashAlgorithm": "SHA-256",
        "acceptedPhase2Manifest": "reports/seo/foundation-file-manifest.json",
        "acceptedPhase2RecordCount": 120,
        "recordCount": len(rows),
        "statusCounts": dict(sorted(Counter(row["status"] for row in rows).items())),
        "categoryCounts": dict(sorted(Counter(row["category"] for row in rows).items())),
        "selfHashVerification": "Set only this manifest record's sha256 to 64 zeroes, stable-serialize, and SHA-256 hash the bytes.",
        "files": rows,
    }


def _finalize(rows: list[dict[str, Any]]) -> bytes:
    self_row = {
        "relativePath": _relative(OUTPUT),
        "category": "PHASE3_EVIDENCE",
        "status": "CREATED",
        "fileSize": 0,
        "sha256": ZERO_HASH,
        "acceptedPhase2Sha256": None,
        "websiteIntegrationStatus": "PROHIBITED",
    }
    rows.append(self_row)
    rows.sort(key=lambda row: row["relativePath"].casefold())
    while True:
        size = len(stable_json_bytes(_payload(rows)))
        if self_row["fileSize"] == size:
            break
        self_row["fileSize"] = size
    self_row["sha256"] = sha256_bytes(stable_json_bytes(_payload(rows)))
    payload = stable_json_bytes(_payload(rows))
    if len(payload) != self_row["fileSize"]:
        raise RuntimeError("Phase 3 manifest self-size did not stabilize")
    return payload


def main() -> int:
    rows = _records()
    payload = _finalize(rows)
    result = atomic_write_bytes(OUTPUT, payload)
    manifest = read_json(OUTPUT)
    print({"status": "PASS", "recordCount": manifest["recordCount"], "statusCounts": manifest["statusCounts"], "output": result})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
