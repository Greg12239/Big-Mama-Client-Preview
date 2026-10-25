from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from _common import CACHE_DIR, DATA_DIR, PREVIEW_DIR, REPORTS_DIR, ROOT, atomic_write_json, ensure_allowed_output, hash_inputs, read_json, utc_now
from _foundation import (
    DATA_FILES,
    build_answer_preview,
    build_local_search_baseline,
    build_metadata_preview,
    build_performance_inventory,
    build_robots_preview,
    build_schema_preview,
    build_sitemap_preview,
    compare_competitor_baseline,
    compare_search_drift,
    detect_placeholders,
    extract_site_data,
    generate_search_report,
    validate_assets,
    validate_internal_links,
    validate_menu_consistency,
    validate_nap,
    validate_schema_preview,
    validate_search_data,
)


@dataclass(frozen=True)
class Component:
    name: str
    action: Callable[[], int]
    inputs: tuple[Path, ...]
    outputs: tuple[Path, ...]


def _data(*names: str) -> tuple[Path, ...]:
    return tuple(DATA_DIR / name for name in names)


ALL_DATA = _data(*DATA_FILES)
PROTECTED_ENTRY = (ROOT / "index.html", ROOT / "styles.css", ROOT / "app.js")
PUBLIC_FILES = tuple(path for path in (ROOT / "public").rglob("*") if path.is_file())
COMPONENTS = (
    Component("extract", extract_site_data, (ROOT / "index.html",), (REPORTS_DIR / "extracted-site-data.json",)),
    Component("metadata", build_metadata_preview, _data("business.json", "production-decisions.json", "content-map.json"), (PREVIEW_DIR / "metadata-preview.html", PREVIEW_DIR / "hreflang-preview.json", PREVIEW_DIR / "manifest-preview.json")),
    Component("schema", build_schema_preview, _data("business.json", "production-decisions.json", "menu.json", "entities.json", "schema-policy.json"), (PREVIEW_DIR / "schema-preview.json",)),
    Component("sitemap", build_sitemap_preview, _data("business.json"), (PREVIEW_DIR / "sitemap-preview.xml",)),
    Component("robots", build_robots_preview, _data("business.json", "crawler-policy.json"), (PREVIEW_DIR / "robots-preview.txt",)),
    Component("answers", build_answer_preview, _data("answer-data.json"), (PREVIEW_DIR / "answer-preview.json",)),
    Component("search-data-validation", validate_search_data, ALL_DATA, (REPORTS_DIR / "seo-validation-report.json",)),
    Component("schema-validation", validate_schema_preview, _data("business.json", "menu.json", "schema-policy.json"), (REPORTS_DIR / "schema-validation-report.json",)),
    Component("nap-validation", validate_nap, _data("business.json", "locations.json") + (ROOT / "index.html",), (REPORTS_DIR / "nap-consistency-report.json",)),
    Component("menu-validation", validate_menu_consistency, _data("menu.json"), (REPORTS_DIR / "menu-consistency-report.json",)),
    Component("asset-validation", validate_assets, _data("image-data.json") + PUBLIC_FILES, (REPORTS_DIR / "asset-validation-report.json",)),
    Component("internal-links", validate_internal_links, (ROOT / "index.html",), (REPORTS_DIR / "internal-link-report.json",)),
    Component("placeholders", detect_placeholders, PROTECTED_ENTRY, (REPORTS_DIR / "placeholder-report.json",)),
    Component("competitors", compare_competitor_baseline, _data("competitor-baseline.json"), (REPORTS_DIR / "competitor-gap-report.json",)),
    Component("local-search-baseline", build_local_search_baseline, _data("business.json", "locations.json", "citations.json", "local-pack-baseline.json"), (REPORTS_DIR / "local-search-baseline.json",)),
    Component("drift", compare_search_drift, _data("data-provenance.json") + PROTECTED_ENTRY, (REPORTS_DIR / "search-drift-report.json",)),
    Component("website-performance-inventory", build_performance_inventory, PROTECTED_ENTRY + PUBLIC_FILES, (REPORTS_DIR / "performance" / "website-performance-inventory.json",)),
    Component("report", generate_search_report, ALL_DATA, (REPORTS_DIR / "SEARCH-DATA-FOUNDATION-REPORT.md",)),
)


def _clear_cache() -> None:
    cache = ensure_allowed_output(CACHE_DIR)
    if not cache.exists():
        return
    for path in sorted(cache.rglob("*"), key=lambda item: len(item.parts), reverse=True):
        if path.is_file():
            path.unlink()
        elif path.is_dir():
            path.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the isolated Big Mama Search Data Foundation")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--no-cache", action="store_true")
    parser.add_argument("--clear-cache", action="store_true")
    parser.add_argument("--cache-status", action="store_true")
    args = parser.parse_args()

    state_path = CACHE_DIR / "build-state.json"
    if args.clear_cache:
        _clear_cache()
    if args.cache_status:
        state = read_json(state_path) if state_path.is_file() else {"status": "EMPTY", "cacheRoot": "reports/seo/.cache"}
        print(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    state = read_json(state_path) if state_path.is_file() and not args.no_cache else {"components": {}}
    previous = state.get("components", {})
    next_state: dict[str, dict[str, object]] = {}
    generated: list[str] = []
    skipped: list[str] = []
    failures: list[dict[str, object]] = []

    for component in COMPONENTS:
        key = hash_inputs(component.inputs)
        outputs_exist = all(path.is_file() for path in component.outputs)
        cache_hit = not args.force and not args.no_cache and previous.get(component.name, {}).get("key") == key and outputs_exist
        if cache_hit:
            skipped.append(component.name)
        else:
            code = component.action()
            if code != 0:
                failures.append({"component": component.name, "exitCode": code})
                break
            generated.append(component.name)
        next_state[component.name] = {"key": key, "outputs": [path.relative_to(ROOT).as_posix() for path in component.outputs]}

    status = "PASS" if not failures else "FAIL"
    cache_payload = {"schemaVersion": "1.0.0", "cacheRoot": "reports/seo/.cache", "components": next_state}
    atomic_write_json(state_path, cache_payload)
    manifest = {
        "schemaVersion": "1.0.0",
        "generatedAt": utc_now(),
        "status": status,
        "dryRun": True,
        "websiteWrites": 0,
        "networkRequests": 0,
        "browserLaunches": 0,
        "cacheRoot": "reports/seo/.cache",
        "generatedComponents": generated,
        "unchangedComponentsSkipped": skipped,
        "failures": failures,
    }
    atomic_write_json(REPORTS_DIR / "search-data-build-manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
