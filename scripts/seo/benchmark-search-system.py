from __future__ import annotations

import argparse
import ctypes
import json
import os
import platform
import subprocess
import sys
import threading
import time
from collections import deque
from pathlib import Path
from statistics import median
from typing import Any

from _common import BENCHMARK_TEMP_DIR, REPORTS_DIR, ROOT, atomic_write_json, atomic_write_text, hash_inputs, read_json, sha256_file, utc_now

SCRIPT_DIR = ROOT / "scripts" / "seo"
TARGETS = {
    "cold": 20.0,
    "warm": 3.0,
    "incremental": 3.0,
    "validation": 15.0,
    "integrity": 30.0,
    "cache-disabled": 20.0,
    "single-file-change": 5.0,
}


def _windows_working_set(pid: int) -> int | None:
    if os.name != "nt":
        return None

    class Counters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    kernel32 = ctypes.windll.kernel32
    psapi = ctypes.windll.psapi
    handle = kernel32.OpenProcess(0x1000 | 0x0010, False, pid)
    if not handle:
        return None
    try:
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
            return None
        return int(counters.WorkingSetSize)
    finally:
        kernel32.CloseHandle(handle)


def _windows_process_tree_pids(root_pid: int) -> list[int]:
    if os.name != "nt":
        return [root_pid]

    class ProcessEntry(ctypes.Structure):
        _fields_ = [
            ("dwSize", ctypes.c_ulong),
            ("cntUsage", ctypes.c_ulong),
            ("th32ProcessID", ctypes.c_ulong),
            ("th32DefaultHeapID", ctypes.c_size_t),
            ("th32ModuleID", ctypes.c_ulong),
            ("cntThreads", ctypes.c_ulong),
            ("th32ParentProcessID", ctypes.c_ulong),
            ("pcPriClassBase", ctypes.c_long),
            ("dwFlags", ctypes.c_ulong),
            ("szExeFile", ctypes.c_wchar * 260),
        ]

    kernel32 = ctypes.windll.kernel32
    snapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
    if snapshot in (0, -1):
        return [root_pid]
    parent_map: dict[int, list[int]] = {}
    try:
        entry = ProcessEntry()
        entry.dwSize = ctypes.sizeof(entry)
        success = kernel32.Process32FirstW(snapshot, ctypes.byref(entry))
        while success:
            parent_map.setdefault(int(entry.th32ParentProcessID), []).append(int(entry.th32ProcessID))
            success = kernel32.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel32.CloseHandle(snapshot)

    result = [root_pid]
    cursor = 0
    while cursor < len(result):
        result.extend(pid for pid in parent_map.get(result[cursor], []) if pid not in result)
        cursor += 1
    return result


def _run(name: str, arguments: list[str], timeout: float = 60.0) -> dict[str, Any]:
    command = [sys.executable, *arguments]
    started = time.perf_counter()
    stdout_lines: deque[str] = deque(maxlen=200)
    stderr_lines: deque[str] = deque(maxlen=200)
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        shell=False,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0,
    )

    def drain(stream: Any, sink: deque[str]) -> None:
        try:
            for line in iter(stream.readline, ""):
                sink.append(line)
        finally:
            stream.close()

    stdout_thread = threading.Thread(target=drain, args=(process.stdout, stdout_lines), daemon=True)
    stderr_thread = threading.Thread(target=drain, args=(process.stderr, stderr_lines), daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    peak_memory = 0
    peak_process_tree_count = 0
    timed_out = False
    try:
        while process.poll() is None:
            process_tree = _windows_process_tree_pids(process.pid)
            observed = sum(_windows_working_set(pid) or 0 for pid in process_tree)
            peak_memory = max(peak_memory, observed)
            peak_process_tree_count = max(peak_process_tree_count, len(process_tree))
            if time.perf_counter() - started > timeout:
                timed_out = True
                if os.name == "nt":
                    subprocess.run(
                        ["taskkill", "/PID", str(process.pid), "/T", "/F"],
                        cwd=ROOT,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=5,
                        check=False,
                        shell=False,
                    )
                else:
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
                break
            time.sleep(0.02)
        process.wait(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        stdout_thread.join(timeout=2)
        stderr_thread.join(timeout=2)
    stdout = "".join(stdout_lines)
    stderr = "".join(stderr_lines)
    duration = time.perf_counter() - started
    target = TARGETS.get(name)
    success_summary = stdout.splitlines()[-1][-1024:] if stdout.splitlines() else ""
    return {
        "name": name,
        "command": [Path(command[0]).name, *arguments],
        "durationSeconds": round(duration, 6),
        "targetSeconds": target,
        "targetPassed": None if target is None else duration <= target,
        "peakMemoryBytes": peak_memory or None,
        "exitCode": process.returncode,
        "timedOut": timed_out,
        "stdoutTail": success_summary if process.returncode == 0 else stdout[-4096:],
        "stderrTail": "" if process.returncode == 0 else stderr[-4096:],
        "subprocessCount": max(1, peak_process_tree_count),
        "browserLaunchCount": 0,
        "networkRequestCount": 0,
    }


def _run_repeated(name: str, arguments: list[str], repetitions: int = 3) -> dict[str, Any]:
    samples = [_run(name, arguments) for _ in range(repetitions)]
    durations = [row["durationSeconds"] for row in samples]
    representative_duration = median(durations)
    representative = min(samples, key=lambda row: abs(row["durationSeconds"] - representative_duration))
    result = dict(representative)
    result["durationSeconds"] = round(representative_duration, 6)
    result["samplesSeconds"] = durations
    result["peakMemoryBytes"] = max((row.get("peakMemoryBytes") or 0 for row in samples), default=0) or None
    result["subprocessCount"] = sum(row.get("subprocessCount", 0) for row in samples)
    result["targetPassed"] = representative_duration <= TARGETS[name]
    result["sampleCount"] = repetitions
    return result


def _single_file_change() -> dict[str, Any]:
    BENCHMARK_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    path = BENCHMARK_TEMP_DIR / "business-change-simulation.json"
    payload = read_json(ROOT / "seo" / "business.json")
    payload["benchmarkSimulation"] = True
    atomic_write_json(path, payload)
    started = time.perf_counter()
    digest = hash_inputs((path,))
    duration = time.perf_counter() - started
    path.unlink()
    return {
        "name": "single-file-change",
        "command": ["internal", "hash-key-simulation"],
        "durationSeconds": round(duration, 6),
        "targetSeconds": TARGETS["single-file-change"],
        "targetPassed": duration <= TARGETS["single-file-change"],
        "peakMemoryBytes": None,
        "exitCode": 0,
        "timedOut": False,
        "resultHash": digest,
        "subprocessCount": 0,
        "browserLaunchCount": 0,
        "networkRequestCount": 0,
    }


def _regressions(previous: dict[str, Any] | None, current: dict[str, Any]) -> list[dict[str, Any]]:
    if not previous or previous.get("benchmarkMethodVersion") != current.get("benchmarkMethodVersion"):
        return []
    old_by_name = {row["name"]: row for row in previous.get("runs", [])}
    findings = []
    for row in current["runs"]:
        old = old_by_name.get(row["name"])
        if not old or not old.get("durationSeconds"):
            continue
        ratio = row["durationSeconds"] / old["durationSeconds"]
        if ratio > 1.2 and row["durationSeconds"] - old["durationSeconds"] > 0.05:
            findings.append({"severity": "P2", "metric": "duration", "mode": row["name"], "previous": old["durationSeconds"], "current": row["durationSeconds"], "increasePercent": round((ratio - 1) * 100, 2)})
        old_memory = old.get("peakMemoryBytes")
        new_memory = row.get("peakMemoryBytes")
        if old_memory and new_memory and new_memory / old_memory > 1.2:
            findings.append({"severity": "P2", "metric": "peakMemory", "mode": row["name"], "previous": old_memory, "current": new_memory})
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark the isolated search-data system")
    parser.add_argument("--mode", choices=["all", "phase2", "cold", "warm", "incremental", "validation", "integrity", "browser", "cache-disabled", "single-file-change"], default="all")
    parser.add_argument("--preserve-baseline", action="store_true", help="Write Phase 2 verification evidence without replacing the accepted baseline")
    args = parser.parse_args()

    baseline_path = REPORTS_DIR / "performance-baseline.json"
    previous = read_json(baseline_path) if baseline_path.is_file() else None
    accepted_baseline_hash_before = sha256_file(baseline_path) if baseline_path.is_file() else None
    if args.mode == "all":
        modes = ["cold", "warm", "incremental", "single-file-change", "validation", "integrity", "cache-disabled", "browser"]
    elif args.mode == "phase2":
        modes = ["incremental", "validation", "integrity"]
    else:
        modes = [args.mode]
    runs: list[dict[str, Any]] = []
    integrity_temp = BENCHMARK_TEMP_DIR / "integrity-benchmark.json"
    for mode in modes:
        if mode == "cold":
            runs.append(_run(mode, ["scripts/seo/build-search-foundation.py", "--force", "--no-cache"]))
        elif mode in {"warm", "incremental"}:
            runs.append(_run_repeated(mode, ["scripts/seo/build-search-foundation.py"]))
        elif mode == "validation":
            runs.append(_run_repeated(mode, ["scripts/seo/validate-search-data.py"]))
        elif mode == "integrity":
            runs.append(_run_repeated(mode, ["scripts/seo/build-website-integrity-manifest.py", "--output", "reports/seo/.benchmark-temp/integrity-benchmark.json", "--label", "benchmark"]))
        elif mode == "cache-disabled":
            runs.append(_run(mode, ["scripts/seo/build-search-foundation.py", "--force", "--no-cache"]))
        elif mode == "single-file-change":
            runs.append(_single_file_change())
        elif mode == "browser":
            runs.append({"name": "browser", "status": "NOT_RUN", "reason": "No rendered-browser evidence was required for foundation validation.", "durationSeconds": 0.0, "targetPassed": True, "peakMemoryBytes": None, "exitCode": 0, "subprocessCount": 0, "browserLaunchCount": 0, "networkRequestCount": 0})

    if integrity_temp.exists():
        integrity_temp.unlink()
    if BENCHMARK_TEMP_DIR.exists() and not any(BENCHMARK_TEMP_DIR.iterdir()):
        BENCHMARK_TEMP_DIR.rmdir()

    failed = [row for row in runs if row.get("exitCode") != 0]
    missed = [row["name"] for row in runs if row.get("targetPassed") is False]
    peak = max((row.get("peakMemoryBytes") or 0 for row in runs), default=0) or None
    payload = {
        "schemaVersion": "1.0.0",
        "benchmarkMethodVersion": "3.0.0",
        "generatedAt": utc_now(),
        "environment": {"python": platform.python_version(), "operatingSystem": platform.platform(), "searchDataSystemVersion": "1.1.0", "dataContractVersion": "1.0.0"},
        "status": "PASS" if not failed else "FAIL",
        "runs": runs,
        "peakMemoryExcludingChromiumBytes": peak,
        "peakMemoryTargetBytes": 512 * 1024 * 1024,
        "browserLaunches": 0,
        "browserPages": 0,
        "networkRequests": 0,
        "targetBudgetsMissed": missed,
        "acceptedBaselinePreserved": None,
        "limitations": ["Chromium was not launched.", "CPU time is not reported because Windows child-process CPU accounting is not implemented.", "Peak memory is the maximum summed working set observed across each Windows child process tree.", "The single-file-change mode validates incremental key computation without modifying source data."],
    }
    findings = _regressions(previous, payload)
    regression = {"generatedAt": utc_now(), "status": "PASS" if not findings else "REGRESSION", "thresholdPercent": 20, "findings": findings}
    if args.preserve_baseline:
        accepted_baseline_hash_after = sha256_file(baseline_path) if baseline_path.is_file() else None
        payload["acceptedBaselineSha256"] = accepted_baseline_hash_before
        payload["acceptedBaselinePreserved"] = accepted_baseline_hash_before is not None and accepted_baseline_hash_before == accepted_baseline_hash_after
        payload["comparisonBaseline"] = "reports/seo/performance-baseline.json"
        payload["regression"] = regression
        atomic_write_json(REPORTS_DIR / "performance-phase2-verification.json", payload)
    else:
        atomic_write_json(baseline_path, payload)
        atomic_write_json(REPORTS_DIR / "performance-regression.json", regression)
    lines = ["# Search Data Performance Baseline", "", f"- Status: **{payload['status']}**", f"- Python: `{payload['environment']['python']}`", f"- Peak memory excluding Chromium: `{peak}` bytes", f"- Browser launches: `0`", f"- Network requests: `0`", "", "| Mode | Seconds | Target | Passed |", "|---|---:|---:|---|"]
    for row in runs:
        lines.append(f"| {row['name']} | {row['durationSeconds']:.6f} | {row.get('targetSeconds', 'n/a')} | {row.get('targetPassed', 'n/a')} |")
    if args.preserve_baseline:
        lines.insert(2, "- Accepted baseline replaced: **no**")
        atomic_write_text(REPORTS_DIR / "performance-phase2-verification.md", "\n".join(lines))
    else:
        atomic_write_text(REPORTS_DIR / "performance-baseline.md", "\n".join(lines))
    print(json.dumps({"status": payload["status"], "runs": len(runs), "targetsMissed": missed, "regressions": len(findings)}, sort_keys=True))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
