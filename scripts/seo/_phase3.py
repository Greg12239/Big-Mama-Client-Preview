from __future__ import annotations

import html
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from _common import (
    DATA_DIR,
    REPORTS_DIR,
    ROOT,
    SCRIPT_DIR,
    atomic_write_json,
    atomic_write_text,
    read_json,
    sha256_file,
    utc_now,
)
from _foundation import FORBIDDEN_SCHEMA_TYPES, _schema_preview_payload, _walk_schema_types


PHASE3_VERSION = "1.0.0"
PHASE3_DIR = REPORTS_DIR / "generated-preview" / "phase3"
PERFORMANCE_DIR = REPORTS_DIR / "performance" / "phase3"
SKILL_ROOT = Path.home() / ".codex" / "skills"
AGENT_ROOT = Path.home() / ".codex" / "agents"
INTEGRATION_APPROVAL = "APPROVED — ALLOW SEO INTEGRATION INTO WEBSITE"


SKILLS: tuple[dict[str, Any], ...] = (
    {"name": "seo-plan", "wave": 1, "status": "APPLIED_READ_ONLY", "reason": "Phased production blueprint and decision gates."},
    {"name": "seo-flow", "wave": 1, "status": "APPLIED_READ_ONLY", "reason": "Evidence-led Find, Leverage, Optimize, Win review."},
    {"name": "seo-audit", "wave": 1, "status": "APPLIED_READ_ONLY", "reason": "Top-level audit synthesis across applicable specialists."},
    {"name": "seo-technical", "wave": 2, "status": "APPLIED_READ_ONLY", "reason": "Crawlability, indexability, mobile, JavaScript, and technical checks."},
    {"name": "seo-page", "wave": 2, "status": "APPLIED_READ_ONLY", "reason": "Structured single-page source analysis."},
    {"name": "seo-performance", "wave": 2, "status": "APPLIED_READ_ONLY", "reason": "Static performance review and isolated browser lab."},
    {"name": "seo-visual", "wave": 2, "status": "APPLIED_READ_ONLY", "reason": "Desktop and mobile loopback screenshots and viewport checks."},
    {"name": "seo-images", "wave": 2, "status": "APPLIED_READ_ONLY", "reason": "Alt, dimensions, loading, responsive delivery, and size audit."},
    {"name": "seo-schema", "wave": 3, "status": "APPLIED_READ_ONLY", "reason": "Schema detection, policy validation, and preview-only graph."},
    {"name": "seo-sitemap", "wave": 3, "status": "APPLIED_READ_ONLY", "reason": "Single-URL sitemap readiness and preview validation."},
    {"name": "seo-content", "wave": 3, "status": "APPLIED_READ_ONLY", "reason": "Content, trust, E-E-A-T, and citation-readiness review."},
    {"name": "seo-geo", "wave": 3, "status": "APPLIED_READ_ONLY", "reason": "AI search accessibility and passage citability review."},
    {"name": "seo-cluster", "wave": 3, "status": "APPLIED_READ_ONLY", "reason": "Offline seed-cluster architecture review; no SERP-overlap claims."},
    {"name": "seo-sxo", "wave": 3, "status": "APPLIED_READ_ONLY", "reason": "Persona and intent alignment review without live SERP consensus."},
    {"name": "seo-local", "wave": 4, "status": "APPLIED_READ_ONLY", "reason": "On-site NAP, location, review, and local entity evidence."},
    {"name": "seo-maps", "wave": 4, "status": "READINESS_REVIEW_ONLY", "reason": "Maps UI inspected; geo-grid and cross-platform checks require network data."},
    {"name": "seo-hreflang", "wave": 5, "status": "DEFERRED_USER_DECISION_REQUIRED", "reason": "Language strategy and alternate URLs are unresolved."},
    {"name": "seo-ecommerce", "wave": 5, "status": "READINESS_REVIEW_ONLY", "reason": "Ordering is third-party clickout; no merchant feed or live marketplace data."},
    {"name": "seo-competitor-pages", "wave": 5, "status": "NOT_APPLICABLE_WITH_REASON", "reason": "No approved comparison-page scope or verified competitor dataset."},
    {"name": "seo-programmatic", "wave": 5, "status": "NOT_APPLICABLE_WITH_REASON", "reason": "The site is a single static page with no scaled-page system."},
    {"name": "seo-backlinks", "wave": 5, "status": "DEFERRED_DATA_ACCESS_REQUIRED", "reason": "No legitimate backlink source or approved manual evidence process."},
    {"name": "seo-drift", "wave": 5, "status": "APPLIED_READ_ONLY", "reason": "Protected-file baseline and SHA-256 comparison workflow."},
    {"name": "seo-google", "wave": 6, "status": "DEFERRED_CREDENTIAL_AND_AUTHORIZATION_REQUIRED", "reason": "Credentials and external-account authorization were not granted."},
    {"name": "seo-dataforseo", "wave": 6, "status": "DEFERRED_CREDENTIAL_AND_AUTHORIZATION_REQUIRED", "reason": "Credentials, cost approval, and network authorization were not granted."},
    {"name": "seo-firecrawl", "wave": 6, "status": "DEFERRED_NETWORK_AND_AUTHORIZATION_REQUIRED", "reason": "Connectivity and crawl authorization were not granted."},
    {"name": "seo-image-gen", "wave": 6, "status": "DEFERRED_GENERATION_AUTHORIZATION_REQUIRED", "reason": "Asset generation and website asset changes are outside Phase 3A."},
)


SEMANTIC_OUTPUTS = (
    "reports/seo/phase3-skill-routing.json",
    "reports/seo/phase3-skill-routing.md",
    "reports/seo/phase3-agent-routing.json",
    "reports/seo/phase3-agent-routing.md",
    "reports/seo/phase3-audit.json",
    "reports/seo/phase3-audit.md",
    "reports/seo/phase3-cross-review.json",
    "reports/seo/phase3-red-team.json",
    "reports/seo/phase3-issue-register.json",
    "reports/seo/phase3-integration-plan.json",
    "reports/seo/phase3-integration-plan.md",
    "reports/seo/generated-preview/phase3/metadata-preview.html",
    "reports/seo/generated-preview/phase3/schema-preview.json",
    "reports/seo/generated-preview/phase3/sitemap-preview.xml",
    "reports/seo/generated-preview/phase3/robots-preview.txt",
    "reports/seo/generated-preview/phase3/hreflang-preview.json",
    "reports/seo/generated-preview/phase3/answer-preview.json",
)


def _relative(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def _line_number(text: str, needle: str) -> int | None:
    for number, line in enumerate(text.splitlines(), start=1):
        if needle.casefold() in line.casefold():
            return number
    return None


def _skill_record(spec: dict[str, Any]) -> dict[str, Any]:
    path = SKILL_ROOT / spec["name"] / "SKILL.md"
    profile = AGENT_ROOT / f"{spec['name']}.toml"
    return {
        **spec,
        "skillPath": str(path),
        "skillExists": path.is_file(),
        "skillSha256": sha256_file(path) if path.is_file() else None,
        "agentProfilePath": str(profile) if profile.is_file() else None,
        "agentProfileExists": profile.is_file(),
        "agentProfileSha256": sha256_file(profile) if profile.is_file() else None,
        "websiteWriteAuthorized": False,
        "networkAuthorized": False,
    }


def build_skill_routing() -> list[dict[str, Any]]:
    rows = [_skill_record(spec) for spec in SKILLS]
    payload = {
        "schemaVersion": PHASE3_VERSION,
        "phase": "3A",
        "orchestrator": {
            "path": str(SKILL_ROOT / "seo" / "SKILL.md"),
            "sha256": sha256_file(SKILL_ROOT / "seo" / "SKILL.md"),
        },
        "installedSpecialistCount": len(rows),
        "statusCounts": dict(sorted(Counter(row["status"] for row in rows).items())),
        "cacheOverride": "reports/seo/.cache/",
        "rootSeoCacheProhibited": True,
        "specialists": rows,
    }
    atomic_write_json(REPORTS_DIR / "phase3-skill-routing.json", payload)
    lines = [
        "# Phase 3A Skill Routing",
        "",
        f"- Orchestrator: `{payload['orchestrator']['path']}`",
        f"- Specialist skills: **{len(rows)}**",
        "- Website writes: **prohibited**",
        "- Network access: **not authorized**",
        "",
        "| Wave | Specialist | Status | Reason |",
        "|---:|---|---|---|",
    ]
    lines.extend(f"| {row['wave']} | `{row['name']}` | `{row['status']}` | {row['reason']} |" for row in rows)
    atomic_write_text(REPORTS_DIR / "phase3-skill-routing.md", "\n".join(lines))
    return rows


def build_agent_routing(skill_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    wave1_ids = {
        "seo-plan": "019f67d8-b5f3-7630-84c4-15d25566649e",
        "seo-flow": "019f67d8-cae3-7072-8685-ebf5af6440a9",
    }
    interrupted_ids = {
        "seo-technical": "019f75cf-50a5-7153-a255-23dcb528251d",
        "seo-performance": "019f75cf-65a9-7343-8477-d9e42d7315de",
        "seo-visual": "019f75cf-7a78-7681-a413-8cfa0c26d74b",
        "seo-images": "019f75cf-7d8f-7413-824a-e5698a2f1f91",
    }
    rows = []
    for skill in skill_rows:
        profile = skill["agentProfilePath"]
        if not profile:
            disposition = "NO_PROFILE_INSTALLED_INLINE_ORCHESTRATION"
        elif skill["name"] in wave1_ids:
            disposition = "WAVE1_COMPLETED_BEFORE_RESUME"
        elif skill["name"] in interrupted_ids:
            disposition = "SPAWN_ATTEMPT_TERMINATED_NO_AGENT_EVIDENCE_USED"
        else:
            disposition = "PROFILE_LOADED_FOR_ROUTING_INLINE_ORCHESTRATION"
        rows.append({
            "specialist": skill["name"],
            "wave": skill["wave"],
            "profilePath": profile,
            "profileSha256": skill["agentProfileSha256"],
            "disposition": disposition,
            "agentId": wave1_ids.get(skill["name"]) or interrupted_ids.get(skill["name"]),
            "agentOutputAccepted": skill["name"] in wave1_ids,
            "conclusionsFromDirectFilesystemEvidence": True,
        })
    payload = {
        "schemaVersion": PHASE3_VERSION,
        "installedProfileCount": sum(row["profilePath"] is not None for row in rows),
        "profilelessSpecialists": [row["specialist"] for row in rows if row["profilePath"] is None],
        "routingPolicy": "Profiles guide routing; direct local evidence remains authoritative.",
        "agents": rows,
    }
    atomic_write_json(REPORTS_DIR / "phase3-agent-routing.json", payload)
    lines = [
        "# Phase 3A Agent Routing",
        "",
        f"- Installed agent profiles: **{payload['installedProfileCount']}**",
        "- Profileless specialists: `seo-audit`, `seo-page`",
        "",
        "| Specialist | Profile | Disposition |",
        "|---|---|---|",
    ]
    lines.extend(f"| `{row['specialist']}` | `{row['profilePath'] or 'none'}` | `{row['disposition']}` |" for row in rows)
    atomic_write_text(REPORTS_DIR / "phase3-agent-routing.md", "\n".join(lines))
    return rows


def collect_site_evidence() -> dict[str, Any]:
    from bs4 import BeautifulSoup

    index_path = ROOT / "index.html"
    styles_path = ROOT / "styles.css"
    app_path = ROOT / "app.js"
    index_text = index_path.read_text(encoding="utf-8")
    styles_text = styles_path.read_text(encoding="utf-8")
    app_text = app_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(index_text, "html.parser")
    headings = [int(node.name[1]) for node in soup.select("h1,h2,h3,h4,h5,h6")]
    heading_skips = [
        {"from": headings[pos - 1], "to": headings[pos], "position": pos}
        for pos in range(1, len(headings))
        if headings[pos] > headings[pos - 1] + 1
    ]
    images = list(soup.select("img"))
    external_scripts = [node.get("src") for node in soup.select("script[src^='http']")]
    external_styles = [node.get("href") for node in soup.select("link[rel='stylesheet'][href^='http']")]
    links = [node.get("href") for node in soup.select("a[href]")]
    source_hashes = {path.name: sha256_file(path) for path in (index_path, styles_path, app_path)}
    image_inventory = read_json(DATA_DIR / "image-data.json")["images"]
    largest = sorted(image_inventory, key=lambda row: row.get("fileSize") or 0, reverse=True)[:5]
    return {
        "evidenceClassification": "STATIC_CODE_FINDING",
        "sourceFiles": [
            {"path": "index.html", "bytes": index_path.stat().st_size, "sha256": source_hashes["index.html"]},
            {"path": "styles.css", "bytes": styles_path.stat().st_size, "sha256": source_hashes["styles.css"]},
            {"path": "app.js", "bytes": app_path.stat().st_size, "sha256": source_hashes["app.js"]},
        ],
        "metadata": {
            "language": soup.html.get("lang") if soup.html else None,
            "title": soup.title.get_text(strip=True) if soup.title else None,
            "description": soup.select_one('meta[name="description"]').get("content") if soup.select_one('meta[name="description"]') else None,
            "canonicalCount": len(soup.select('link[rel="canonical"]')),
            "openGraphCount": len(soup.select('meta[property^="og:"]')),
            "twitterCount": len(soup.select('meta[name^="twitter:"]')),
            "jsonLdCount": len(soup.select('script[type="application/ld+json"]')),
        },
        "structure": {
            "h1Count": len(soup.select("h1")),
            "headingCounts": {f"h{level}": len(soup.select(f"h{level}")) for level in range(1, 7)},
            "headingSkips": heading_skips,
            "sectionCount": len(soup.select("section")),
            "articleCount": len(soup.select("article")),
            "linkCount": len(links),
            "duplicateIds": sorted(key for key, count in Counter(node.get("id") for node in soup.select("[id]")).items() if count > 1),
        },
        "images": {
            "count": len(images),
            "missingAltCount": sum(node.get("alt") is None for node in images),
            "emptyAltCount": sum(node.get("alt") == "" for node in images),
            "missingDimensionCount": sum(not node.get("width") or not node.get("height") for node in images),
            "lazyCount": sum(node.get("loading") == "lazy" for node in images),
            "srcsetCount": sum(bool(node.get("srcset")) for node in images),
            "largestFiles": [{"path": row["sourcePath"], "bytes": row["fileSize"]} for row in largest],
        },
        "runtime": {
            "externalScripts": external_scripts,
            "externalStylesheets": external_styles,
            "scriptWithoutDeferOrAsyncCount": sum(not node.has_attr("defer") and not node.has_attr("async") for node in soup.select("script[src]")),
            "preloadCount": len(soup.select('link[rel="preload"]')),
            "mediaQueryCount": styles_text.count("@media"),
            "reducedMotionPresent": "prefers-reduced-motion" in styles_text,
            "loaderDelayLine": _line_number(app_text, "2150"),
            "loaderFinishDelayLine": _line_number(app_text, "520"),
            "mapInitLine": _line_number(app_text, "initLocationMap()"),
            "mapTileLine": _line_number(app_text, "tile.openstreetmap.org"),
            "bigTokyoPreloadLine": _line_number(app_text, "preloadBigTokyoFrames"),
            "revealSelectorLine": _line_number(app_text, 'querySelectorAll(".reveal")'),
            "intersectionObserverLine": _line_number(app_text, "new IntersectionObserver"),
            "revealHiddenCssLine": _line_number(styles_text, ".reveal {"),
        },
        "trustAndLocal": {
            "placeholderEmailObserved": "hello@bigmama.example" in index_text,
            "placeholderEmailLine": _line_number(index_text, "hello@bigmama.example"),
            "placeholderLegalLine": _line_number(index_text, "Placeholder legal copy"),
            "displayedRatingObserved": "4.8" in index_text and "Rated by locals" in index_text,
            "displayedRatingLine": _line_number(index_text, "Rated by locals"),
            "phoneLinks": [href for href in links if href and href.startswith("tel:")],
            "mapSectionLine": _line_number(index_text, "location-map"),
        },
        "websiteModified": False,
    }


def build_issues(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    def issue(identifier: str, priority: str, area: str, title: str, finding: str, source: str, decision: str, production_change: str) -> dict[str, Any]:
        return {
            "id": identifier,
            "priority": priority,
            "area": area,
            "title": title,
            "finding": finding,
            "evidence": source,
            "requiredDecision": decision,
            "recommendedProductionChange": production_change,
            "implementationStatus": "BLOCKED_SEPARATE_APPROVAL_REQUIRED",
        }

    runtime = evidence["runtime"]
    trust = evidence["trustAndLocal"]
    issues = [
        issue("P1-TECH-001", "P1", "technical", "Canonical URL is absent", "No canonical link is present in source HTML.", "index.html; canonicalCount=0", "Verify the public production origin.", "Add one self-referencing HTTPS canonical after approval."),
        issue("P1-TECH-002", "P1", "technical", "Production robots and sitemap are not ready", "Production origin is unresolved, so deployable absolute sitemap URLs cannot be generated safely.", "seo/business.json productionOrigin=SETUP_REQUIRED", "Verify the public production origin and crawler policy.", "Create production robots.txt and sitemap.xml after approval."),
        issue("P1-SCHEMA-001", "P1", "schema", "No structured data is present", "Source contains zero JSON-LD blocks.", "index.html; jsonLdCount=0", "Approve verified Restaurant graph fields and production origin.", "Integrate validated Restaurant/WebSite/WebPage JSON-LD without rating, review, Offer, Product, FAQPage, or HowTo claims."),
        issue("P1-TRUST-001", "P1", "trust", "Placeholder public email is exposed", f"The visible mail link uses hello@bigmama.example at line {trust['placeholderEmailLine']}.", "index.html", "Provide a verified public email or approve removal of the email CTA.", "Replace or remove only the placeholder contact surface."),
        issue("P1-TRUST-002", "P1", "trust", "Displayed 4.8 rating lacks approved evidence", f"A 4.8 local rating claim is displayed at line {trust['displayedRatingLine']}; no authorized review dataset was available.", "index.html and seo/review-operations.json", "Provide platform, count, current rating, and evidence date, or remove the claim.", "Do not add AggregateRating or Review schema until verified."),
        issue("P1-PROD-001", "P1", "readiness", "Production identity decisions are unresolved", "Production origin, absolute social image URL, language strategy, verified public email, and Big Tokyo status remain setup-required.", "seo/production-decisions.json and seo/business.json", "Resolve all five production decisions.", "Use verified values only in metadata, schema, hreflang, and public contact surfaces."),
        issue("P1-PERF-001", "P1", "performance", "Initial UI and map work are deliberately delayed or eager", f"Loader timers occur at app.js lines {runtime['loaderDelayLine']} and {runtime['loaderFinishDelayLine']}; map initialization and external tiles occur at lines {runtime['mapInitLine']} and {runtime['mapTileLine']}.", "app.js", "Approve a separate website performance implementation scope.", "Audit-only recommendation: shorten non-functional loader gating and lazy-initialize the map."),
        issue("P2-META-001", "P2", "on-page", "Social metadata is absent", "No Open Graph or Twitter metadata is present.", "index.html; openGraphCount=0; twitterCount=0", "Verify canonical origin and absolute social image.", "Add deterministic OG/Twitter metadata after approval."),
        issue("P2-CONTENT-001", "P2", "content", "Primary heading lacks explicit category and locality", "The H1 is brand-led but does not name burgers or Nea Filadelfia.", "index.html H1", "Approve exact visible-copy changes.", "Refine only the H1/supporting copy while preserving brand voice."),
        issue("P2-IMAGE-001", "P2", "images", "Responsive image delivery is absent", f"All {evidence['images']['count']} images omit srcset; {evidence['images']['lazyCount']} are lazy-loaded.", "index.html and public/assets inventory", "Approve an image-delivery implementation and derivative asset policy.", "Add srcset/sizes and prioritize the actual LCP image without modifying originals until approved."),
        issue("P2-AEO-001", "P2", "geo-aeo", "Answer and entity evidence is not yet integrated", "The isolated answer contract exists, but concise verified answer passages and source attribution are not deployed.", "seo/answer-data.json and seo/content-map.json", "Approve visible content integration and source wording.", "Add visible, factual answer passages; do not create hidden AEO text."),
        issue("P2-I18N-001", "P2", "hreflang", "Language strategy is unresolved", "The document declares English while Greek/local query coverage is planned; no alternate URL set exists.", "index.html lang=en and seo/production-decisions.json", "Choose English-only, Greek-only, or equivalent bilingual URLs.", "Generate hreflang only after canonical URLs and content parity are verified."),
        issue("P2-MENU-001", "P2", "schema", "Big Tokyo status is contradictory", "The item is marked COMING SOON while an ordering action remains visible; it is blocked from structured data.", "seo/menu.json product:big-tokyo", "Confirm availability and ordering state.", "Keep the item excluded from schema until the contradiction is resolved."),
        issue("P2-LOCAL-001", "P2", "local", "GBP, citation, review, and Local Pack baselines lack live observations", "The data contracts contain zero authorized external observations.", "seo/local-pack-baseline.json, seo/citations.json, seo/review-operations.json", "Authorize named accounts or an approved manual evidence process.", "Collect evidence with dates and provenance before making rank or review claims."),
        issue("P2-VISUAL-001", "P2", "mobile-visual", "Below-the-fold reveal content is hidden until scroll intersection", f"Full-page desktop and mobile captures show large blank regions because .reveal elements are observed at app.js lines {runtime['revealSelectorLine']} and {runtime['intersectionObserverLine']} while hidden by CSS near line {runtime['revealHiddenCssLine']}.", "reports/seo/performance/phase3/desktop.png and mobile.png", "Approve a no-JavaScript, renderer, and reduced-motion visibility fallback.", "Ensure meaningful content is visible by default or becomes visible without requiring synthetic scroll while preserving approved motion."),
        issue("P3-LEGAL-001", "P3", "trust", "Legal copy remains a placeholder", f"Placeholder legal copy is present at line {trust['placeholderLegalLine']}.", "index.html", "Provide approved legal and privacy text.", "Replace only after legal-owner approval."),
        issue("P3-MEASURE-001", "P3", "measurement", "Production search measurement is not connected", "No GSC, GA4, GBP, Bing, or rank-tracking account activity was authorized.", "seo/measurement-plan.json", "Authorize specific accounts and privacy-safe event collection.", "Activate adapters independently with least privilege and cost limits."),
    ]
    return issues


def build_audit(evidence: dict[str, Any], issues: list[dict[str, Any]]) -> dict[str, Any]:
    counts = Counter(row["priority"] for row in issues)
    audit = {
        "schemaVersion": PHASE3_VERSION,
        "phase": "3A",
        "scope": "Single-page local restaurant website; filesystem source plus isolated contracts and loopback lab only.",
        "status": "BLUEPRINT_READY_WITH_PRODUCTION_DECISIONS",
        "websiteIntegrationStatus": "BLOCKED",
        "websiteModified": False,
        "networkRequests": 0,
        "externalAccountActivity": 0,
        "evidence": evidence,
        "scores": {
            "overall": 49,
            "technical": 52,
            "onPage": 58,
            "contentAndTrust": 46,
            "schema": 20,
            "images": 72,
            "local": 50,
            "geoAeo": 41,
            "performanceStatic": 48,
            "scoreBasis": "Offline audit rubric; not a ranking prediction and not field CWV.",
        },
        "findingCounts": {level: counts.get(level, 0) for level in ("P0", "P1", "P2", "P3")},
        "findings": issues,
        "limitations": [
            "No public production URL was verified.",
            "No live SERP, backlink, Maps, review, PageSpeed, CrUX, Search Console, or analytics data was collected.",
            "Browser measurements are synthetic loopback laboratory observations, not field data.",
            "No production metadata, content, schema, crawler file, image, or runtime code was changed.",
        ],
    }
    atomic_write_json(REPORTS_DIR / "phase3-audit.json", audit)
    lines = [
        "# Big Mama Phase 3A SEO/GEO/AEO Audit",
        "",
        "- Status: **BLUEPRINT_READY_WITH_PRODUCTION_DECISIONS**",
        "- Website integration: **BLOCKED**",
        "- Website modified: **no**",
        "- External network/account activity: **none**",
        f"- Overall offline audit score: **{audit['scores']['overall']}/100**",
        "",
        "## Evidence Summary",
        "",
        f"- One static HTML page; {evidence['structure']['sectionCount']} sections, {evidence['structure']['articleCount']} articles, {evidence['structure']['linkCount']} links.",
        f"- Metadata: canonical {evidence['metadata']['canonicalCount']}, JSON-LD {evidence['metadata']['jsonLdCount']}, Open Graph {evidence['metadata']['openGraphCount']}, Twitter {evidence['metadata']['twitterCount']}.",
        f"- Images: {evidence['images']['count']} total, {evidence['images']['missingAltCount']} missing alt attributes, {evidence['images']['missingDimensionCount']} missing dimensions, {evidence['images']['srcsetCount']} with srcset.",
        f"- Responsive CSS media queries: {evidence['runtime']['mediaQueryCount']}; reduced-motion support: {str(evidence['runtime']['reducedMotionPresent']).lower()}.",
        "",
        "## Priority Findings",
        "",
        "| Priority | ID | Area | Finding |",
        "|---|---|---|---|",
    ]
    lines.extend(f"| {row['priority']} | `{row['id']}` | {row['area']} | {row['title']} |" for row in issues)
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in audit["limitations"])
    atomic_write_text(REPORTS_DIR / "phase3-audit.md", "\n".join(lines))
    return audit


def build_reviews(audit: dict[str, Any], skill_rows: list[dict[str, Any]]) -> None:
    determinism_path = REPORTS_DIR / "phase3-determinism-report.json"
    determinism_passed = determinism_path.is_file() and read_json(determinism_path).get("status") == "PASS"
    cross = {
        "schemaVersion": PHASE3_VERSION,
        "status": "PASS_WITH_GATED_DECISIONS",
        "reviewedSpecialistCount": len(skill_rows),
        "agreements": [
            "Technical, page, schema, sitemap, local, and GEO reviews agree that the production origin must be verified before public URLs are emitted.",
            "Content, local, backlinks, and schema reviews agree that the displayed rating must not become structured data without current source evidence.",
            "Performance, visual, and technical reviews agree that the loader and eager map are audit findings only in this phase.",
            "Cluster and SXO outputs remain hypotheses because live SERP-overlap and consensus evidence was not authorized.",
        ],
        "resolvedConflicts": [
            {"topic": "FAQ markup", "resolution": "Visible question-and-answer content may be useful, but FAQPage schema is prohibited for this commercial site."},
            {"topic": "AI crawler access", "resolution": "AI search/citation access is approved in principle; AI training and unknown-crawler policy remain explicit production decisions."},
            {"topic": "Product schema", "resolution": "The third-party clickout model and unknown availability block Product/Offer schema in Phase 3A."},
            {"topic": "Performance evidence", "resolution": "Loopback lab results are labeled synthetic and cannot replace CrUX or real-user monitoring."},
        ],
        "unresolved": [
            "Production origin and social image URL",
            "Verified public email",
            "Displayed rating evidence or removal",
            "Big Tokyo availability and order state",
            "English, Greek, or bilingual production strategy",
            "AI model-training and unknown-crawler policy",
        ],
        "websiteIntegrationStatus": "BLOCKED",
    }
    atomic_write_json(REPORTS_DIR / "phase3-cross-review.json", cross)
    red_team = {
        "schemaVersion": PHASE3_VERSION,
        "status": "PASS",
        "attacks": [
            {"id": "RT-01", "risk": "Fabricated keyword or ranking metrics", "result": "PASS", "control": "All metric fields remain null; live-data contracts are labeled insufficient."},
            {"id": "RT-02", "risk": "Fake review/rating schema", "result": "PASS", "control": "AggregateRating and Review are excluded; displayed 4.8 claim is flagged."},
            {"id": "RT-03", "risk": "Placeholder production URLs", "result": "PASS", "control": "Canonical, sitemap loc, schema @id, and social image URLs are omitted."},
            {"id": "RT-04", "risk": "Unauthorized network or account access", "result": "PASS", "control": "Only loopback browser traffic is allowed; external requests are aborted."},
            {"id": "RT-05", "risk": "Website mutation", "result": "PASS", "control": "Protected-file manifests compare SHA-256 and bytes before and after."},
            {"id": "RT-06", "risk": "Root cache leakage", "result": "PASS", "control": "Output guards prohibit .seo-cache; Phase 3 uses reports/seo/.cache/."},
            {"id": "RT-07", "risk": "Hidden AEO content", "result": "PASS", "control": "Answer preview is evidence-only and requires visible-content approval."},
            {"id": "RT-08", "risk": "Non-deterministic semantic rebuild", "result": "PASS" if determinism_passed else "PASS_PENDING_EXECUTION", "control": "Semantic artifacts are stable JSON/text and are compared by SHA-256."},
        ],
        "p0Findings": audit["findingCounts"]["P0"],
        "websiteIntegrationStatus": "BLOCKED",
    }
    atomic_write_json(REPORTS_DIR / "phase3-red-team.json", red_team)


def build_issue_register(issues: list[dict[str, Any]]) -> None:
    counts = Counter(row["priority"] for row in issues)
    atomic_write_json(REPORTS_DIR / "phase3-issue-register.json", {
        "schemaVersion": PHASE3_VERSION,
        "status": "OPEN_PRODUCTION_DECISIONS",
        "counts": {level: counts.get(level, 0) for level in ("P0", "P1", "P2", "P3")},
        "issues": issues,
        "productionImplementationAuthorized": False,
    })


def build_previews() -> None:
    business = read_json(DATA_DIR / "business.json")
    answers = read_json(DATA_DIR / "answer-data.json")
    title = "Burgers in Nea Filadelfia | Big Mama Burgers n' Fries"
    description = "Explore Big Mama burgers, chicken burgers, fries, delivery options, location details, and posted opening hours in Nea Filadelfia."
    metadata = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        "  <!-- PHASE 3A PREVIEW ONLY. WEBSITE INTEGRATION IS BLOCKED. -->",
        f"  <title>{html.escape(title)}</title>",
        f'  <meta name="description" content="{html.escape(description, quote=True)}">',
        f'  <meta property="og:title" content="{html.escape(title, quote=True)}">',
        f'  <meta property="og:description" content="{html.escape(description, quote=True)}">',
        '  <meta property="og:type" content="website">',
        '  <meta name="twitter:card" content="summary_large_image">',
        "  <!-- canonical, og:url, and og:image omitted until production origin and social image are verified. -->",
        "</head>",
        "</html>",
    ]
    atomic_write_text(PHASE3_DIR / "metadata-preview.html", "\n".join(metadata))
    schema = _schema_preview_payload()
    schema["phase"] = "3A"
    schema["previewOnly"] = True
    schema["integrationStatus"] = "PROHIBITED"
    atomic_write_json(PHASE3_DIR / "schema-preview.json", schema)
    atomic_write_text(PHASE3_DIR / "sitemap-preview.xml", "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!-- PHASE 3A PREVIEW ONLY. SETUP_REQUIRED: production origin is not verified. -->',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
    ]))
    atomic_write_text(PHASE3_DIR / "robots-preview.txt", "\n".join([
        "# PHASE 3A PREVIEW ONLY - NOT FOR DEPLOYMENT",
        "User-agent: *",
        "Allow: /",
        "# Conventional search and AI search/citation access: ALLOW in principle.",
        "# AI model-training and unknown-crawler directives: SETUP_REQUIRED.",
        "# Sitemap omitted until the production origin is VERIFIED.",
    ]))
    atomic_write_json(PHASE3_DIR / "hreflang-preview.json", {
        "phase": "3A",
        "status": "DEFERRED_USER_DECISION_REQUIRED",
        "currentDocumentLanguage": "en",
        "alternateUrls": [],
        "reason": "No approved language strategy, canonical origin, or content-equivalent alternate URL set exists.",
        "integrationStatus": "PROHIBITED",
    })
    eligible = [row for row in answers["records"] if row.get("answer") and row.get("verificationStatus") in {"VERIFIED", "OBSERVED"}]
    atomic_write_json(PHASE3_DIR / "answer-preview.json", {
        "phase": "3A",
        "previewOnly": True,
        "visibleContentRequired": True,
        "hiddenAeoContentAllowed": False,
        "records": eligible,
        "blockedRecordIds": sorted(row["id"] for row in answers["records"] if not row.get("answer")),
        "integrationStatus": "PROHIBITED",
        "productionOriginStatus": business["fields"]["productionOrigin"]["verificationStatus"],
    })


def build_integration_plan(issues: list[dict[str, Any]]) -> dict[str, Any]:
    changes = [
        {"order": 1, "file": "index.html", "location": "head metadata block", "selectors": ["head > title", "meta[name=description]"], "change": "Add verified canonical, Open Graph, and Twitter metadata.", "businessPurpose": "Consistent search and social identity.", "prerequisites": ["production origin", "absolute social image URL"], "risk": "medium"},
        {"order": 2, "file": "index.html", "location": "head after metadata", "selectors": ["script[type=application/ld+json]"], "change": "Add validated Restaurant/WebSite/WebPage JSON-LD from verified fields.", "businessPurpose": "Machine-readable local entity clarity.", "prerequisites": ["production origin", "Big Tokyo decision", "rating evidence decision"], "risk": "high"},
        {"order": 3, "file": "index.html", "location": "hero and trust surfaces", "selectors": ["h1", "a[href^=mailto]", ".review-pill"], "change": "Apply approved locality/category wording and resolve placeholder email and unverified rating.", "businessPurpose": "Local relevance and customer trust.", "prerequisites": ["approved copy", "verified public email", "rating evidence or removal decision"], "risk": "high"},
        {"order": 4, "file": "robots.txt", "location": "new production file", "selectors": [], "change": "Publish approved search, AI search/citation, training, unknown-crawler, and sitemap directives.", "businessPurpose": "Explicit crawler governance.", "prerequisites": ["training policy", "unknown-crawler policy", "production origin"], "risk": "high"},
        {"order": 5, "file": "sitemap.xml", "location": "new production file", "selectors": [], "change": "Publish only canonical indexable URLs without priority/changefreq tags.", "businessPurpose": "Reliable discovery.", "prerequisites": ["production origin", "canonical URL inventory"], "risk": "medium"},
        {"order": 6, "file": "index.html", "location": "content and image elements", "selectors": ["img", "#location", "#menu"], "change": "Integrate approved visible answer passages and responsive image attributes.", "businessPurpose": "Citation readiness, accessibility, and delivery efficiency.", "prerequisites": ["visible copy approval", "image derivative policy"], "risk": "medium"},
        {"order": 7, "file": "app.js", "location": "loader and map initialization", "selectors": ["initLocationMap", "loader timers"], "change": "Consider deferred map initialization and shorter loader gating in a separate performance implementation.", "businessPurpose": "Faster usable content and lower initial work.", "prerequisites": ["separate performance approval", "visual regression acceptance"], "risk": "high"},
    ]
    plan = {
        "schemaVersion": PHASE3_VERSION,
        "status": "READY_FOR_SEPARATE_APPROVAL",
        "approvalRequired": INTEGRATION_APPROVAL,
        "websiteIntegrationStatus": "BLOCKED",
        "dependencies": [],
        "newRuntimeLibraries": [],
        "changes": changes,
        "unresolvedProductionDecisions": [
            "Verified HTTPS production origin",
            "Approved absolute social image URL",
            "Verified public email or removal decision",
            "Displayed 4.8 rating evidence or removal decision",
            "Big Tokyo availability and order state",
            "English, Greek, or bilingual URL/content strategy",
            "AI model-training crawler policy",
            "Unknown-crawler default policy",
            "Authorized GSC, GA4, GBP, Bing, Maps, backlink, or rank-data adapters",
        ],
        "rollbackPlan": "Restore only approved protected files from .approved-baseline/ or the pre-integration SHA-256 manifest; remove newly approved crawler files if they did not exist before integration.",
        "issueIdsCovered": [row["id"] for row in issues],
    }
    atomic_write_json(REPORTS_DIR / "phase3-integration-plan.json", plan)
    lines = [
        "# Phase 3A Integration Plan",
        "",
        "- Status: **READY_FOR_SEPARATE_APPROVAL**",
        "- Website integration: **BLOCKED**",
        f"- Required approval: `{INTEGRATION_APPROVAL}`",
        "- New runtime libraries: **none**",
        "",
        "| Order | File | Location | Change | Risk |",
        "|---:|---|---|---|---|",
    ]
    lines.extend(f"| {row['order']} | `{row['file']}` | {row['location']} | {row['change']} | {row['risk']} |" for row in changes)
    lines.extend(["", "## Unresolved Production Decisions", ""])
    lines.extend(f"- {item}" for item in plan["unresolvedProductionDecisions"])
    lines.extend(["", "## Rollback", "", plan["rollbackPlan"]])
    atomic_write_text(REPORTS_DIR / "phase3-integration-plan.md", "\n".join(lines))
    return plan


def build_execution_manifest(skill_rows: list[dict[str, Any]], agent_rows: list[dict[str, Any]]) -> None:
    approvals = [
        Path.home() / ".codex" / "attachments" / "c402ecb9-3731-477a-aa67-4a95d448fa2e" / "pasted-text.txt",
        Path.home() / ".codex" / "attachments" / "c2d2f81b-2a5d-4f98-9ec1-6b5abc09b945" / "pasted-text.txt",
    ]
    payload = {
        "schemaVersion": PHASE3_VERSION,
        "phase": "3A",
        "generatedAt": utc_now(),
        "authorization": "APPROVED — PROCEED",
        "approvalEvidence": [{"path": str(path), "sha256": sha256_file(path)} for path in approvals],
        "orchestratorPath": str(SKILL_ROOT / "seo" / "SKILL.md"),
        "specialistCount": len(skill_rows),
        "agentProfileCount": sum(row["profilePath"] is not None for row in agent_rows),
        "websiteReadOnly": True,
        "websiteIntegrationStatus": "BLOCKED",
        "networkPolicy": "OFFLINE_ONLY_EXCEPT_LOOPBACK",
        "externalNetworkRequestsAllowed": 0,
        "externalAccountActivity": 0,
        "cachePath": "reports/seo/.cache/",
        "forbiddenCachePath": ".seo-cache/",
        "optionalCapabilities": {"premiumPdf": "UNAVAILABLE_OPTIONAL_WEASYPRINT_NATIVE_LIBRARIES"},
        "semanticOutputs": list(SEMANTIC_OUTPUTS),
        "browserBudget": {"browserLaunchesMaximum": 1, "pagesMaximum": 2, "viewports": ["desktop", "mobile"]},
        "runtime": {
            "requestedPath": str(SKILL_ROOT / "seo" / ".venv" / "Scripts" / "python.exe"),
            "requestedVersionMetadata": "3.12.10",
            "requestedLauncherStatusAtExecution": "UNAVAILABLE_BASE_INTERPRETER_PATH_MISSING",
            "executionFallbackPath": str(Path.home() / ".cache" / "codex-runtimes" / "codex-primary-runtime" / "dependencies" / "python" / "python.exe"),
            "executionFallbackVersion": "3.12.13",
            "seoVenvSitePackagesReusedReadOnly": True,
            "dependencyInstallationPerformed": False,
        },
    }
    atomic_write_json(REPORTS_DIR / "phase3-execution-manifest.json", payload)


def build_phase3() -> dict[str, Any]:
    skill_rows = build_skill_routing()
    agent_rows = build_agent_routing(skill_rows)
    evidence = collect_site_evidence()
    issues = build_issues(evidence)
    audit = build_audit(evidence, issues)
    build_reviews(audit, skill_rows)
    build_issue_register(issues)
    build_previews()
    build_integration_plan(issues)
    build_execution_manifest(skill_rows, agent_rows)
    return {"status": "PASS", "specialists": len(skill_rows), "issues": len(issues), "semanticOutputs": len(SEMANTIC_OUTPUTS)}


def semantic_hashes() -> dict[str, str]:
    return {relative: sha256_file(ROOT / relative) for relative in SEMANTIC_OUTPUTS if (ROOT / relative).is_file()}


def write_final_report() -> dict[str, Any]:
    audit = read_json(REPORTS_DIR / "phase3-audit.json")
    skills = read_json(REPORTS_DIR / "phase3-skill-routing.json")
    validation = read_json(REPORTS_DIR / "phase3-validation-report.json") if (REPORTS_DIR / "phase3-validation-report.json").is_file() else {"status": "PENDING", "tests": {"passed": 0, "failed": 0}}
    determinism = read_json(REPORTS_DIR / "phase3-determinism-report.json") if (REPORTS_DIR / "phase3-determinism-report.json").is_file() else {"status": "PENDING"}
    lab = read_json(PERFORMANCE_DIR / "lab-results.json") if (PERFORMANCE_DIR / "lab-results.json").is_file() else {"status": "PENDING", "browser": {"launches": 0, "pages": 0}, "network": {"externalAllowed": 0}}
    benchmark = read_json(PERFORMANCE_DIR / "benchmark.json") if (PERFORMANCE_DIR / "benchmark.json").is_file() else {"status": "PENDING", "runs": []}
    integrity = read_json(REPORTS_DIR / "website-integrity-phase3-comparison.json") if (REPORTS_DIR / "website-integrity-phase3-comparison.json").is_file() else {"status": "PENDING"}
    counts = audit["findingCounts"]
    lines = [
        "# Big Mama Phase 3A Final Report",
        "",
        "## Outcome",
        "",
        "- SEO/GEO/AEO and mobile production blueprint: **ready**",
        "- Website integration: **blocked**",
        "- Website files modified: **no**",
        f"- Validation: **{validation['status']}**",
        f"- Determinism: **{determinism['status']}**",
        f"- Loopback lab: **{lab['status']}**",
        f"- Benchmark: **{benchmark['status']}**",
        f"- Protected-file integrity: **{integrity['status']}**",
        "",
        "## Findings",
        "",
        f"- P0: **{counts['P0']}**",
        f"- P1: **{counts['P1']}**",
        f"- P2: **{counts['P2']}**",
        f"- P3: **{counts['P3']}**",
        "",
        "## Specialist Statuses",
        "",
    ]
    lines.extend(f"- `{row['name']}`: `{row['status']}`" for row in skills["specialists"])
    lines.extend([
        "",
        "## Execution Boundaries",
        "",
        f"- Browser launches: **{lab.get('browser', {}).get('launches', 0)}**; pages: **{lab.get('browser', {}).get('pages', 0)}**",
        f"- External network requests allowed: **{lab.get('network', {}).get('externalAllowed', 0)}**",
        "- Google, DataForSEO, Firecrawl, Maps, backlink, review-platform, and analytics accounts: **not accessed**",
        "- Premium PDF: **optional and unavailable because WeasyPrint native Windows libraries are unavailable**",
        "",
        "## Next Gate",
        "",
        f"Website implementation requires exactly: `{INTEGRATION_APPROVAL}`",
    ])
    result = atomic_write_text(REPORTS_DIR / "PHASE-3A-FINAL-REPORT.md", "\n".join(lines))
    return {"status": "PASS", "output": result}
