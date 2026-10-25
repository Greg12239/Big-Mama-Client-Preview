from __future__ import annotations

import json
import os
import subprocess
import sys

from _common import REPORTS_DIR, ROOT, atomic_write_json, utc_now
from _phase3 import SEMANTIC_OUTPUTS, semantic_hashes


def _build() -> dict[str, object]:
    process = subprocess.run(
        [sys.executable, "scripts/seo/run-phase3a.py"],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
        check=False,
        shell=False,
    )
    return {
        "exitCode": process.returncode,
        "stdoutTail": process.stdout.splitlines()[-1][-1024:] if process.stdout.splitlines() else "",
        "stderrTail": process.stderr[-2048:] if process.returncode else "",
    }


def main() -> int:
    initial = semantic_hashes()
    first_run = _build()
    first = semantic_hashes()
    second_run = _build()
    second = semantic_hashes()
    expected = set(SEMANTIC_OUTPUTS)
    missing = sorted(expected - set(second))
    changed = sorted(path for path in expected if initial.get(path) != first.get(path) or first.get(path) != second.get(path))
    status = "PASS" if first_run["exitCode"] == second_run["exitCode"] == 0 and not missing and not changed else "FAIL"
    report = {
        "schemaVersion": "1.0.0",
        "generatedAt": utc_now(),
        "status": status,
        "semanticOutputCount": len(second),
        "expectedSemanticOutputCount": len(expected),
        "missingOutputs": missing,
        "changedOutputs": changed,
        "runs": [first_run, second_run],
        "executionManifestExcluded": True,
        "reasonForExclusion": "Execution timestamps are operational evidence, not semantic blueprint content.",
        "subprocessCount": 2,
        "browserLaunchCount": 0,
        "networkRequestCount": 0,
    }
    atomic_write_json(REPORTS_DIR / "phase3-determinism-report.json", report)
    print(json.dumps({"status": status, "semanticOutputs": len(second), "changed": changed, "missing": missing}, sort_keys=True))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

