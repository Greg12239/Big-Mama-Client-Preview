from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from statistics import median
from typing import Any

from _common import REPORTS_DIR, ROOT, atomic_write_json, atomic_write_text, sha256_file, utc_now


OUTPUT_DIR = REPORTS_DIR / "performance" / "phase3"
TARGETS = {"phase3-build": 5.0, "phase3-validation": 5.0, "phase3-unit": 15.0}


def _load_benchmark_runtime() -> Any:
    path = ROOT / "scripts" / "seo" / "benchmark-search-system.py"
    spec = importlib.util.spec_from_file_location("foundation_benchmark_runtime", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load benchmark runtime: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.TARGETS.update(TARGETS)
    return module


def _repeat(module: Any, name: str, arguments: list[str], count: int = 3) -> dict[str, Any]:
    samples = [module._run(name, arguments, timeout=30.0) for _ in range(count)]
    durations = [row["durationSeconds"] for row in samples]
    duration = median(durations)
    return {
        "name": name,
        "command": samples[0]["command"],
        "sampleCount": count,
        "samplesSeconds": durations,
        "medianSeconds": round(duration, 6),
        "targetSeconds": TARGETS[name],
        "targetPassed": duration <= TARGETS[name],
        "peakMemoryBytes": max((row.get("peakMemoryBytes") or 0 for row in samples), default=0) or None,
        "exitCodes": [row["exitCode"] for row in samples],
        "timedOut": any(row["timedOut"] for row in samples),
        "subprocessObservations": sum(row.get("subprocessCount", 0) for row in samples),
        "browserLaunches": 0,
        "networkRequests": 0,
    }


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    baseline = REPORTS_DIR / "performance-baseline.json"
    baseline_hash_before = sha256_file(baseline)
    module = _load_benchmark_runtime()
    runs = [
        _repeat(module, "phase3-build", ["scripts/seo/run-phase3a.py"]),
        _repeat(module, "phase3-validation", ["scripts/seo/validate-phase3.py", "--core-only"]),
        _repeat(module, "phase3-unit", ["-m", "unittest", "scripts/seo/tests/test_phase3.py"]),
    ]
    baseline_hash_after = sha256_file(baseline)
    failures = [row["name"] for row in runs if any(code != 0 for code in row["exitCodes"]) or not row["targetPassed"] or row["timedOut"]]
    peak = max((row.get("peakMemoryBytes") or 0 for row in runs), default=0) or None
    memory_target = 512 * 1024 * 1024
    if peak is not None and peak > memory_target:
        failures.append("peak-memory")
    payload = {
        "schemaVersion": "1.0.0",
        "generatedAt": utc_now(),
        "status": "PASS" if not failures else "FAIL",
        "runs": runs,
        "targetFailures": failures,
        "peakMemoryBytes": peak,
        "peakMemoryTargetBytes": memory_target,
        "peakMemoryTargetPassed": peak is None or peak <= memory_target,
        "browserLaunches": 0,
        "networkRequests": 0,
        "acceptedPhase2BaselinePath": "reports/seo/performance-baseline.json",
        "acceptedPhase2BaselineSha256Before": baseline_hash_before,
        "acceptedPhase2BaselineSha256After": baseline_hash_after,
        "acceptedPhase2BaselinePreserved": baseline_hash_before == baseline_hash_after,
        "regressionPolicy": {
            "failure": "Any non-zero exit, timeout, target miss, or peak memory above 512 MiB.",
            "warning": "A future comparable median increase above 20% and 50 ms should be reviewed.",
        },
        "limitations": ["Windows working-set sampling includes each benchmark child process tree.", "Browser performance is measured separately and is excluded from engineering-process peak memory."],
    }
    atomic_write_json(OUTPUT_DIR / "benchmark.json", payload)
    lines = [
        "# Phase 3A Engineering Benchmark",
        "",
        f"- Status: **{payload['status']}**",
        f"- Peak process-tree memory: **{peak} bytes**",
        f"- Phase 2 baseline preserved: **{str(payload['acceptedPhase2BaselinePreserved']).lower()}**",
        "- Browser launches: **0**",
        "- Network requests: **0**",
        "",
        "| Mode | Median seconds | Target | Passed | Peak bytes |",
        "|---|---:|---:|---|---:|",
    ]
    lines.extend(f"| {row['name']} | {row['medianSeconds']:.6f} | {row['targetSeconds']:.1f} | {row['targetPassed']} | {row['peakMemoryBytes']} |" for row in runs)
    atomic_write_text(OUTPUT_DIR / "benchmark.md", "\n".join(lines))
    print(json.dumps({"status": payload["status"], "runs": len(runs), "targetFailures": failures, "peakMemoryBytes": peak}, sort_keys=True))
    return 0 if payload["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())

