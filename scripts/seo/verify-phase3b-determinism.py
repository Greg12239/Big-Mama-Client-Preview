from __future__ import annotations

import json

from _common import REPORTS_DIR, ROOT, atomic_write_json, sha256_file
from _phase3b import SEMANTIC_OUTPUTS, build_phase3b, validate_phase3b


def hashes() -> dict[str, str]:
    return {path: sha256_file(ROOT / path) for path in SEMANTIC_OUTPUTS if (ROOT / path).is_file()}


before = hashes()
build_phase3b()
validate_phase3b()
after = hashes()
changed = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
payload = {
    "schemaVersion": "1.0.0", "status": "PASS" if not changed else "FAIL",
    "outputCount": len(after), "changedOutputs": changed, "beforeHashes": before, "afterHashes": after,
    "excludedOperationalOutputs": ["phase3b-determinism-report.json", "phase3b-file-manifest.json", "website integrity manifests", "PHASE-3B-FINAL-REPORT.md"],
}
atomic_write_json(REPORTS_DIR / "phase3b-determinism-report.json", payload)
print(json.dumps({"status": payload["status"], "changed": len(changed)}, sort_keys=True))
raise SystemExit(0 if not changed else 2)

