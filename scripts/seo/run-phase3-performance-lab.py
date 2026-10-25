from __future__ import annotations

import json
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from _common import REPORTS_DIR, ROOT, atomic_write_json, sha256_file, utc_now


OUTPUT_DIR = REPORTS_DIR / "performance" / "phase3"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:
        return


def _local_host(url: str) -> bool:
    return (urlparse(url).hostname or "").casefold() in {"127.0.0.1", "localhost"}


def _evaluate(page: Any) -> dict[str, Any]:
    return page.evaluate(
        """
        () => {
          const nav = performance.getEntriesByType('navigation')[0];
          const paints = Object.fromEntries(performance.getEntriesByType('paint').map(x => [x.name, x.startTime]));
          const map = document.querySelector('[data-location-map], #location-map, .location-map');
          const h1 = document.querySelector('h1');
          const loader = document.querySelector('[data-loader]');
          const rect = el => el ? ({
            x: el.getBoundingClientRect().x,
            y: el.getBoundingClientRect().y,
            width: el.getBoundingClientRect().width,
            height: el.getBoundingClientRect().height
          }) : null;
          const resources = performance.getEntriesByType('resource');
          return {
            navigation: nav ? {
              responseStartMs: nav.responseStart,
              domContentLoadedMs: nav.domContentLoadedEventEnd,
              loadEventMs: nav.loadEventEnd,
              transferSizeBytes: nav.transferSize,
              decodedBodySizeBytes: nav.decodedBodySize
            } : null,
            firstContentfulPaintMs: paints['first-contentful-paint'] ?? null,
            largestContentfulPaintMs: window.__phase3Perf?.lcp ?? null,
            cumulativeLayoutShift: window.__phase3Perf?.cls ?? 0,
            longTaskCount: window.__phase3Perf?.longTasks?.length ?? 0,
            longTaskTotalMs: (window.__phase3Perf?.longTasks ?? []).reduce((sum, value) => sum + value, 0),
            resourceCount: resources.length,
            resourceTransferBytes: resources.reduce((sum, value) => sum + (value.transferSize || 0), 0),
            horizontalOverflowPx: Math.max(0, document.documentElement.scrollWidth - window.innerWidth),
            bodyLoaded: document.body.classList.contains('is-loaded'),
            loaderHidden: loader ? loader.classList.contains('is-hidden') : true,
            h1Visible: !!(h1 && h1.getBoundingClientRect().width && h1.getBoundingClientRect().height),
            h1Rect: rect(h1),
            mapRect: rect(map),
            viewport: {width: window.innerWidth, height: window.innerHeight, devicePixelRatio: window.devicePixelRatio}
          };
        }
        """
    )


def main() -> int:
    from playwright.sync_api import sync_playwright

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    handler = partial(QuietHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    target = f"http://127.0.0.1:{server.server_port}/index.html"
    viewports = (
        {"name": "desktop", "width": 1440, "height": 900, "deviceScaleFactor": 1},
        {"name": "mobile", "width": 390, "height": 844, "deviceScaleFactor": 1},
    )
    results: list[dict[str, Any]] = []
    external_attempts: list[str] = []
    local_requests = 0
    browser_launches = 0
    page_count = 0
    fatal_error: str | None = None
    browser = None
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            browser_launches = 1
            for viewport in viewports:
                context = browser.new_context(
                    viewport={"width": viewport["width"], "height": viewport["height"]},
                    device_scale_factor=viewport["deviceScaleFactor"],
                    is_mobile=viewport["name"] == "mobile",
                )
                page = context.new_page()
                page_count += 1
                console_errors: list[str] = []
                page_errors: list[str] = []
                failed_requests: list[dict[str, str]] = []
                counters = {"local": 0}

                def route_request(route: Any) -> None:
                    if _local_host(route.request.url):
                        route.continue_()
                    else:
                        external_attempts.append(route.request.url)
                        route.abort("blockedbyclient")

                def request_seen(request: Any) -> None:
                    if _local_host(request.url):
                        counters["local"] += 1

                page.route("**/*", route_request)
                page.on("request", request_seen)
                page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
                page.on("pageerror", lambda error: page_errors.append(str(error)))
                page.on("requestfailed", lambda request: failed_requests.append({"url": request.url, "error": request.failure or "failed"}))
                page.add_init_script(
                    """
                    window.__phase3Perf = {lcp: null, cls: 0, longTasks: []};
                    try { new PerformanceObserver(list => {
                      const entries = list.getEntries();
                      if (entries.length) window.__phase3Perf.lcp = entries[entries.length - 1].startTime;
                    }).observe({type: 'largest-contentful-paint', buffered: true}); } catch (e) {}
                    try { new PerformanceObserver(list => {
                      for (const entry of list.getEntries()) if (!entry.hadRecentInput) window.__phase3Perf.cls += entry.value;
                    }).observe({type: 'layout-shift', buffered: true}); } catch (e) {}
                    try { new PerformanceObserver(list => {
                      for (const entry of list.getEntries()) window.__phase3Perf.longTasks.push(entry.duration);
                    }).observe({type: 'longtask', buffered: true}); } catch (e) {}
                    """
                )
                response = page.goto(target, wait_until="domcontentloaded", timeout=15000)
                try:
                    page.wait_for_function("document.body.classList.contains('is-loaded')", timeout=5000)
                except Exception:
                    pass
                page.wait_for_timeout(500)
                metrics = _evaluate(page)
                screenshot = OUTPUT_DIR / f"{viewport['name']}.png"
                page.screenshot(path=str(screenshot), full_page=True)
                local_requests += counters["local"]
                results.append({
                    "name": viewport["name"],
                    "configuredViewport": {"width": viewport["width"], "height": viewport["height"]},
                    "httpStatus": response.status if response else None,
                    "metrics": metrics,
                    "consoleErrors": console_errors,
                    "pageErrors": page_errors,
                    "failedExternalRequests": [row for row in failed_requests if not _local_host(row["url"])],
                    "screenshot": {
                        "path": screenshot.relative_to(ROOT).as_posix(),
                        "bytes": screenshot.stat().st_size,
                        "sha256": sha256_file(screenshot),
                    },
                })
                context.close()
            browser.close()
            browser = None
    except Exception as exc:
        fatal_error = f"{type(exc).__name__}: {exc}"
        if browser is not None:
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)

    failed_viewports = [row["name"] for row in results if row["httpStatus"] != 200 or row["metrics"]["horizontalOverflowPx"] > 0 or row["pageErrors"]]
    status = "PASS" if fatal_error is None and len(results) == 2 and not failed_viewports else "FAIL"
    payload = {
        "schemaVersion": "1.0.0",
        "generatedAt": utc_now(),
        "status": status,
        "evidenceClassification": "SYNTHETIC_LOOPBACK_LAB",
        "fieldDataStatus": "FIELD_DATA_UNAVAILABLE",
        "websitePerformanceScope": "AUDIT_ONLY",
        "websiteOptimizationApplied": False,
        "browser": {"engine": "chromium", "headless": True, "launches": browser_launches, "pages": page_count},
        "network": {
            "policy": "LOOPBACK_ONLY",
            "localRequests": local_requests,
            "externalAttempted": len(external_attempts),
            "externalAllowed": 0,
            "blockedExternalUrls": sorted(set(external_attempts)),
        },
        "viewports": results,
        "failedViewports": failed_viewports,
        "fatalError": fatal_error,
        "limitations": [
            "Loopback timing is not production hosting performance.",
            "External Leaflet and OpenStreetMap resources were deliberately blocked.",
            "No CrUX, PageSpeed, RUM, or network-throttled field-equivalent data was collected.",
        ],
    }
    atomic_write_json(OUTPUT_DIR / "lab-results.json", payload)
    print(json.dumps({"status": status, "browserLaunches": browser_launches, "pages": page_count, "externalAllowed": 0, "failedViewports": failed_viewports}, sort_keys=True))
    return 0 if status == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
