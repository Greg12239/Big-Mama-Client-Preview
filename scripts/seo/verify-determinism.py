from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from _common import DATA_DIR, PREVIEW_DIR, REPORTS_DIR, ROOT, atomic_write_json, sha256_file, utc_now


def semantic_hashes() -> dict[str, str]:
    paths = [path for path in DATA_DIR.glob("*.json") if path.is_file()]
    paths.extend(path for path in PREVIEW_DIR.rglob("*") if path.is_file())
    return {
        path.relative_to(ROOT).as_posix(): sha256_file(path)
        for path in sorted(paths, key=lambda item: item.relative_to(ROOT).as_posix().casefold())
    }


def main() -> int:
    before = semantic_hashes()
    process = subprocess.run(
        [sys.executable, "scripts/seo/build-search-foundation.py", "--force", "--no-cache"],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        check=False,
        shell=False,
    )
    after = semantic_hashes()
    changed = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
    report = {
        "generatedAt": utc_now(),
        "status": "PASS" if process.returncode == 0 and not changed else "FAIL",
        "semanticOutputCount": len(after),
        "changedOutputs": changed,
        "buildExitCode": process.returncode,
        "subprocessCount": 1,
        "browserLaunchCount": 0,
        "networkRequestCount": 0,
        "stdoutSummary": process.stdout.splitlines()[-1][-1024:] if process.stdout.splitlines() else "",
        "stderrSummary": process.stderr[-2048:] if process.returncode else "",
    }
    result = atomic_write_json(REPORTS_DIR / "determinism-report.json", report)
    print(json.dumps({"report": result, "status": report["status"], "changedOutputCount": len(changed)}, sort_keys=True))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
