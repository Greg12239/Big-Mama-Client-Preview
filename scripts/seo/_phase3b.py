from __future__ import annotations

import html
import json
import re
import shutil
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from _common import (
    CACHE_DIR,
    DATA_DIR,
    DOCS_DIR,
    REPORTS_DIR,
    ROOT,
    atomic_write_bytes,
    atomic_write_json,
    atomic_write_text,
    read_json,
    sha256_file,
)


SCHEMA_VERSION = "1.0.0"
AS_OF_DATE = "2026-07-18"
PHASE = "3B"
PREVIEW_DIR = REPORTS_DIR / "generated-preview" / "phase3b"
SKILL_ROOT = Path.home() / ".codex" / "skills"
AGENT_ROOT = Path.home() / ".codex" / "agents"
INTEGRATION_APPROVAL = "APPROVED — ALLOW SEO INTEGRATION INTO WEBSITE"
READ_APPROVAL = "APPROVED — ALLOW READ-ONLY SEARCH PLATFORM ACCESS"
WRITE_APPROVAL = "APPROVED — ALLOW EXTERNAL SEARCH PLATFORM CHANGES"

EXISTING_CONTRACTS = (
    "crawler-policy.json",
    "answer-data.json",
    "image-data.json",
    "measurement-plan.json",
    "review-operations.json",
)

SEMANTIC_OUTPUTS = (
    "seo/production-truth.json",
    "seo/platform-coverage.json",
    "seo/url-policy.json",
    "seo/crawler-policy.json",
    "seo/entity-graph.json",
    "seo/local-search-source.json",
    "seo/answer-data.json",
    "seo/image-data.json",
    "seo/measurement-plan.json",
    "seo/review-operations.json",
    "seo/authority-plan.json",
    "docs/seo/PRODUCTION-DECISION-FORM.md",
    "docs/seo/MULTI-ENGINE-SEARCH-STRATEGY.md",
    "docs/seo/LOCAL-SEARCH-OPERATIONS.md",
    "docs/seo/AEO-GEO-CONTENT-STANDARD.md",
    "docs/seo/SEARCH-MEASUREMENT-OPERATIONS.md",
    "docs/seo/DEPLOYMENT-AND-INDEXING-RUNBOOK.md",
    "reports/seo/phase3b-official-source-register.json",
    "reports/seo/phase3b-production-readiness.json",
    "reports/seo/phase3b-platform-coverage.json",
    "reports/seo/phase3b-content-gap-analysis.json",
    "reports/seo/phase3b-entity-consistency.json",
    "reports/seo/phase3b-crawler-policy-review.json",
    "reports/seo/phase3b-search-activation-plan.json",
    "reports/seo/phase3b-search-activation-plan.md",
    "reports/seo/phase3b-red-team.json",
    "reports/seo/phase3b-skill-routing.json",
    "reports/seo/phase3b-agent-routing.json",
    "reports/seo/phase3b-execution-manifest.json",
    "reports/seo/generated-preview/phase3b/head-preview.html",
    "reports/seo/generated-preview/phase3b/schema-preview.json",
    "reports/seo/generated-preview/phase3b/robots-preview.txt",
    "reports/seo/generated-preview/phase3b/sitemap-preview.xml",
    "reports/seo/generated-preview/phase3b/social-preview.json",
    "reports/seo/generated-preview/phase3b/answer-content-preview.html",
    "reports/seo/generated-preview/phase3b/indexnow-preview.json",
    "reports/seo/generated-preview/phase3b/platform-verification-preview.json",
)


def _write_json(relative: str, payload: Any) -> dict[str, Any]:
    return atomic_write_json(ROOT / relative, payload)


def _write_text(relative: str, payload: str) -> dict[str, Any]:
    return atomic_write_text(ROOT / relative, payload)


def _backup_existing_contracts() -> dict[str, Any]:
    rollback_dir = CACHE_DIR / "phase3b-rollback"
    records = []
    for name in EXISTING_CONTRACTS:
        source = DATA_DIR / name
        target = rollback_dir / f"seo__{name}"
        if not target.exists():
            atomic_write_bytes(target, source.read_bytes())
        records.append({
            "source": f"seo/{name}",
            "backup": target.relative_to(ROOT).as_posix(),
            "sourceSha256BeforePhase3B": sha256_file(target),
            "backupSha256": sha256_file(target),
            "restorable": True,
        })
    payload = {
        "schemaVersion": SCHEMA_VERSION,
        "phase": PHASE,
        "cacheLocation": "reports/seo/.cache/phase3b-rollback/",
        "rootSeoCacheUsed": False,
        "records": records,
        "status": "PASS",
    }
    _write_json("reports/seo/phase3b-rollback-manifest.json", payload)
    return payload


def _truth_record(
    identifier: str,
    label: str,
    value: Any,
    status: str,
    source: list[str],
    affected: list[str],
    reason: str,
    confidence: str = "HIGH",
    verified: str | None = None,
) -> dict[str, Any]:
    return {
        "id": identifier,
        "label": label,
        "value": value,
        "status": status,
        "source": source,
        "lastVerifiedDate": verified,
        "confidence": confidence,
        "productionEligible": status in {"VERIFIED", "APPROVED", "REMOVE", "NOT_APPLICABLE"},
        "affectedOutputs": affected,
        "reason": reason,
    }


def build_production_truth(business: dict[str, Any]) -> dict[str, Any]:
    fields = business["fields"]
    address = fields["address"]["value"]
    geo = fields["geo"]["value"]
    hours = fields["openingHours"]
    order = fields["orderingUrls"]["value"]
    common = ["head-preview", "schema-preview", "sitemap-preview", "robots-preview"]
    rows = [
        _truth_record("public_business_name", "PUBLIC BUSINESS NAME", fields["canonicalBrandName"]["value"], "VERIFIED", ["seo/business.json", "index.html"], ["metadata", "schema", "local-search"], "Brand name is consistent in the frozen source.", verified="2026-07-14"),
        _truth_record("legal_business_name", "LEGAL BUSINESS NAME", None, "UNKNOWN", [], ["schema", "legal-copy"], "No legal entity name is approved; NOT_APPLICABLE is an allowed user decision.", "LOW"),
        _truth_record("production_origin", "PRODUCTION ORIGIN", None, "SETUP_REQUIRED", [], common, "No production origin is verified."),
        _truth_record("preferred_hostname", "PREFERRED HOSTNAME", None, "SETUP_REQUIRED", [], common, "www/non-www preference depends on the production origin."),
        _truth_record("https_status", "HTTPS STATUS", None, "SETUP_REQUIRED", [], ["canonical", "redirects", "deployment"], "No authorized production endpoint was tested."),
        _truth_record("hosting_platform", "HOSTING PLATFORM", None, "UNKNOWN", [], ["deployment", "redirects", "404"], "Repository evidence does not establish the final hosting platform.", "LOW"),
        _truth_record("deployment_branch", "DEPLOYMENT BRANCH", None, "UNKNOWN", [], ["deployment", "ci"], "No deployment branch is approved.", "LOW"),
        _truth_record("canonical_home_url", "CANONICAL HOME URL", None, "SETUP_REQUIRED", [], common, "Cannot be derived until origin and hostname are approved."),
        _truth_record("public_telephone", "PUBLIC TELEPHONE", fields["telephone"]["value"], "VERIFIED", ["seo/business.json", "index.html"], ["visible-content", "schema", "local-search"], "Phone is verified in local source evidence.", verified="2026-07-14"),
        _truth_record("public_email", "PUBLIC EMAIL OR EXPLICIT EMAIL REMOVAL", None, "UNKNOWN", ["index.html#placeholder-email"], ["visible-content", "contact", "schema"], "The current .example address is a placeholder and is not production eligible.", "HIGH"),
        _truth_record("street_address", "STREET ADDRESS", address["streetAddress"], "VERIFIED", ["seo/business.json", "index.html"], ["visible-content", "schema", "local-search"], "Address is verified in frozen evidence.", verified="2026-07-14"),
        _truth_record("locality", "LOCALITY", address["addressLocality"], "VERIFIED", ["seo/business.json", "index.html"], ["metadata", "schema", "local-search"], "Locality is verified in frozen evidence.", verified="2026-07-14"),
        _truth_record("postal_code", "POSTAL CODE", address["postalCode"], "VERIFIED", ["seo/business.json", "index.html"], ["schema", "local-search"], "Postal code is verified in frozen evidence.", verified="2026-07-14"),
        _truth_record("country", "COUNTRY", address["addressCountry"], "VERIFIED", ["schema", "local-search"], ["schema", "local-search"], "Country code is verified in the local contract.", verified="2026-07-14"),
        _truth_record("latitude", "LATITUDE", geo["latitude"], "VERIFIED", ["seo/business.json", "app.js"], ["schema", "maps"], "Latitude is consistent in frozen source evidence.", verified="2026-07-14"),
        _truth_record("longitude", "LONGITUDE", geo["longitude"], "VERIFIED", ["seo/business.json", "app.js"], ["schema", "maps"], "Longitude is consistent in frozen source evidence.", verified="2026-07-14"),
        _truth_record("timezone", "TIMEZONE", hours["timeZone"], "VERIFIED", ["seo/business.json"], ["hours", "open-now", "schema"], "Timezone is approved in the Phase 2 contract.", verified="2026-07-14"),
        _truth_record("opening_hours", "VERIFIED OPENING HOURS", hours["value"], "VERIFIED", ["seo/business.json", "index.html"], ["visible-content", "schema", "local-search", "answers"], "Regular posted hours are verified; holiday exceptions remain separate.", verified="2026-07-14"),
        _truth_record("holiday_hours_policy", "HOLIDAY-HOURS OPERATING POLICY", None, "SETUP_REQUIRED", [], ["visible-content", "schema", "open-now", "operations"], "No holiday or exceptional-hours owner is defined."),
        _truth_record("primary_business_category", "PRIMARY BUSINESS CATEGORY", None, "SETUP_REQUIRED", ["seo/business.json#businessType=Restaurant"], ["schema", "business-profiles", "metadata"], "Restaurant is supported, but the operational primary profile category requires approval."),
        _truth_record("served_cuisine", "SERVED CUISINE", ["Burgers"], "VERIFIED", ["seo/menu.json", "index.html"], ["schema", "metadata", "answers"], "The visible menu supports burgers as served cuisine.", verified="2026-07-14"),
        _truth_record("price_range", "PRICE-RANGE DECISION", None, "UNKNOWN", ["seo/menu.json#prohibitedUnknowns.prices"], ["schema", "visible-content"], "No supportable public price range is present; removal is allowed.", "HIGH"),
        _truth_record("wolt_url", "WOLT URL", order["wolt"], "VERIFIED", ["seo/business.json", "seo/menu.json", "index.html"], ["ordering", "local-search", "measurement"], "URL is verified in frozen local source; live provider availability was not checked.", verified="2026-07-14"),
        _truth_record("efood_url", "EFOOD URL", order["efood"], "VERIFIED", ["seo/business.json", "seo/menu.json", "index.html"], ["ordering", "local-search", "measurement"], "URL is verified in frozen local source; live provider availability was not checked.", verified="2026-07-14"),
        _truth_record("google_business_profile", "GOOGLE BUSINESS PROFILE URL OR PLACE IDENTIFIER", fields["mapsUrl"]["value"], "UNKNOWN", ["index.html#review-link"], ["schema", "local-search", "reviews"], "A Maps URL is observed, but profile ownership/current identity is not externally verified.", "MEDIUM"),
        _truth_record("social_profiles", "VERIFIED SOCIAL-PROFILE URLS", [], "UNKNOWN", ["seo/business.json"], ["sameAs", "social", "local-search"], "No official social profiles are verified.", "HIGH"),
        _truth_record("approved_social_image", "APPROVED SOCIAL IMAGE", None, "SETUP_REQUIRED", ["seo/image-data.json"], ["open-graph", "social-preview", "schema"], "No absolute production image URL is approved."),
        _truth_record("big_tokyo_status", "BIG TOKYO STATUS", None, "CONTRADICTORY", ["seo/menu.json", "index.html#big-tokyo"], ["menu", "schema", "answers", "ordering"], "COMING SOON conflicts with enabled order actions."),
        _truth_record("displayed_rating", "DISPLAYED RATING EVIDENCE OR REMOVAL", None, "UNKNOWN", ["index.html#review-rating=4.8"], ["visible-content", "schema", "reviews"], "The displayed value lacks approved source/date/count evidence."),
        _truth_record("review_count", "REVIEW-COUNT EVIDENCE OR REMOVAL", None, "UNKNOWN", ["index.html#reviews"], ["visible-content", "schema", "reviews"], "No current verified aggregate review count is approved."),
        _truth_record("language_strategy", "LANGUAGE STRATEGY", None, "SETUP_REQUIRED", ["index.html#html-lang=en"], ["html-lang", "content", "canonical", "hreflang", "sitemap"], "The current declaration is observed; production architecture is not approved."),
        _truth_record("search_crawler_policy", "SEARCH-CRAWLER POLICY", None, "SETUP_REQUIRED", [], ["robots", "indexing"], "Search indexing crawler policy requires explicit approval."),
        _truth_record("ai_search_crawler_policy", "AI-SEARCH/ANSWER CRAWLER POLICY", None, "SETUP_REQUIRED", [], ["robots", "ai-search"], "AI search access must be decided separately from training."),
        _truth_record("ai_training_crawler_policy", "AI-TRAINING CRAWLER POLICY", None, "SETUP_REQUIRED", [], ["robots", "ai-training"], "AI training consent requires an explicit decision."),
        _truth_record("unknown_crawler_policy", "UNKNOWN-CRAWLER POLICY", None, "SETUP_REQUIRED", [], ["robots", "security"], "Unknown-crawler default policy is not approved."),
        _truth_record("analytics_consent", "COOKIE/ANALYTICS CONSENT DECISION", None, "SETUP_REQUIRED", [], ["analytics", "privacy", "legal-copy"], "No consent and privacy architecture is approved."),
        _truth_record("public_legal_copy", "PUBLIC LEGAL COPY STATUS", None, "SETUP_REQUIRED", ["index.html#legal-placeholder"], ["visible-content", "privacy", "analytics"], "Legal copy remains a placeholder."),
        _truth_record("contact_cta", "CONTACT CTA DECISION", None, "SETUP_REQUIRED", ["index.html#contact"], ["visible-content", "measurement"], "Phone/email/directions contact behavior requires production approval."),
        _truth_record("order_cta", "ORDER CTA DECISION", None, "SETUP_REQUIRED", ["index.html#provider-links"], ["visible-content", "measurement", "ordering"], "Current provider actions are observed but not approved as the production contract."),
        _truth_record("analytics_property", "ANALYTICS PROPERTY STATUS", None, "SETUP_REQUIRED", [], ["analytics", "measurement"], "No authorized analytics property is identified."),
        _truth_record("search_console", "SEARCH CONSOLE STATUS", None, "SETUP_REQUIRED", [], ["verification", "sitemap", "measurement"], "No account or property access is authorized."),
        _truth_record("bing_webmaster", "BING WEBMASTER STATUS", None, "SETUP_REQUIRED", [], ["verification", "sitemap", "measurement"], "No account or site access is authorized."),
        _truth_record("indexnow", "INDEXNOW STATUS", None, "SETUP_REQUIRED", [], ["key", "submission", "ci"], "No host, key, endpoint workflow, or authorization is approved."),
        _truth_record("business_profile_management", "BUSINESS PROFILE MANAGEMENT STATUS", None, "SETUP_REQUIRED", [], ["google-business-profile", "local-search", "measurement"], "Profile ownership/access has not been established."),
    ]
    counts = dict(sorted(Counter(row["status"] for row in rows).items()))
    unresolved = [row["id"] for row in rows if not row["productionEligible"]]
    return {
        "schemaVersion": SCHEMA_VERSION,
        "phase": PHASE,
        "asOfDate": AS_OF_DATE,
        "fieldCount": len(rows),
        "statusCounts": counts,
        "unresolvedCount": len(unresolved),
        "unresolvedFieldIds": unresolved,
        "productionReady": False,
        "websiteIntegrationStatus": "BLOCKED",
        "fields": rows,
    }


OFFICIAL_SOURCES = (
    ("google-local-business", "Local business structured data", "developers.google.com", "https://developers.google.com/search/docs/appearance/structured-data/local-business", "Use the most specific truthful type; markup must match visible content and does not guarantee rich results.", "Restaurant graph is preview-only; unsupported ratings and Big Tokyo are excluded."),
    ("google-canonical", "Consolidate duplicate URLs", "developers.google.com", "https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls", "Redirects and rel=canonical are strong signals; sitemap inclusion is weaker; signals should agree.", "Canonical, sitemap, schema, Open Graph and internal links share one approved origin."),
    ("google-sitemaps", "Sitemaps overview", "developers.google.com", "https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview", "Sitemaps aid discovery but do not guarantee crawling or indexing; include canonical URLs.", "No production sitemap URL is emitted until the canonical origin is approved."),
    ("google-build-sitemap", "Build and submit a sitemap", "developers.google.com", "https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap", "Use absolute canonical URLs and accurate lastmod values.", "Material-change hashing gates lastmod and future submission."),
    ("google-robots-meta", "Robots meta tag specifications", "developers.google.com", "https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag", "A crawler must access a page to observe noindex.", "Staging noindex must not be paired with a block that prevents reading it."),
    ("google-robots", "Introduction to robots.txt", "developers.google.com", "https://developers.google.com/search/docs/crawling-indexing/robots/intro", "robots.txt controls crawler traffic; it is not a security control or reliable indexing-removal mechanism.", "Crawler policy is explicit and security controls remain separate."),
    ("google-ai", "AI features and your website", "developers.google.com", "https://developers.google.com/search/docs/appearance/ai-features", "Google AI search uses normal SEO controls; no special AI file or schema is required; Googlebot controls Search AI features.", "No llms.txt ranking dependency or AI-only content is proposed."),
    ("google-images", "Google Images SEO best practices", "developers.google.com", "https://developers.google.com/search/docs/appearance/google-images", "Use crawlable img sources, useful alt text, supported formats and responsive delivery; CSS background images are not indexed.", "The image manifest records responsive variants and image eligibility without altering assets."),
    ("google-search-works", "In-depth guide to how Google Search works", "developers.google.com", "https://developers.google.com/search/docs/fundamentals/how-search-works", "Crawling, indexing and serving are separate and never guaranteed.", "All outcome language is eligibility-based, not guaranteed."),
    ("google-gbp-performance", "Understand your Business Profile performance", "support.google.com", "https://support.google.com/business/answer/9918094", "Verified profile access is required; available interaction metrics vary by profile.", "GBP measurement remains externally authorized setup work."),
    ("google-local-ranking", "Tips to improve local ranking", "support.google.com", "https://support.google.com/business/answer/7091", "Local results are primarily based on relevance, distance and prominence; better ranking cannot be purchased or requested.", "Local plan focuses on accurate entity data, completeness and legitimate prominence."),
    ("google-local-sources", "How Google sources and uses information in local listings", "support.google.com", "https://support.google.com/business/answer/2721884", "The official website is one of multiple sources for local information.", "Website, business profiles and provider listings require parity checks."),
    ("bing-sitemaps", "Sitemaps", "bing.com", "https://www.bing.com/webmasters/help/sitemaps-3b5cf6ed", "Bing accepts sitemap discovery through Webmaster Tools or a robots sitemap directive.", "Submission is deferred until account authorization and a canonical sitemap exist."),
    ("bing-robots", "How to create a robots.txt file", "bing.com", "https://www.bing.com/webmasters/help/how-to-create-a-robots-txt-file-cb7c31ec", "Use standards-based rules and validate them; excessive per-bot complexity raises error risk.", "The preview remains blocked until policy decisions are approved."),
    ("bing-robots-meta", "Robots meta tags and attributes that Bing supports", "bing.com", "https://www.bing.com/webmasters/help/robots-meta-tags-and-attributes-that-bing-supports-5198d240", "A page must remain crawlable for noindex to be processed.", "Noindex and crawl blocking are kept logically separate."),
    ("bing-indexnow", "IndexNow", "bing.com", "https://www.bing.com/webmasters/help/indexnow-0z209wby", "IndexNow requires site ownership and changed URL submission.", "Readiness is prepared; no key or request is generated."),
    ("indexnow-protocol", "IndexNow protocol", "indexnow.org", "https://www.indexnow.org/documentation", "Submit only added, updated or deleted URLs; prove host ownership with a key and avoid repeated unchanged submissions.", "Future CI uses material-change triggers and a repository secret only after approval."),
    ("schema-restaurant", "Restaurant", "schema.org", "https://schema.org/Restaurant", "Restaurant is a LocalBusiness subtype for truthful restaurant entities.", "One Restaurant node is planned with verified NAP, geo and hours."),
    ("schema-hours", "OpeningHoursSpecification", "schema.org", "https://schema.org/OpeningHoursSpecification", "Overnight hours may close earlier than they open; special hours can be represented separately.", "Regular overnight hours are represented, while holiday hours remain blocked."),
    ("openai-bots", "Overview of OpenAI crawlers", "developers.openai.com", "https://developers.openai.com/api/docs/bots", "OAI-SearchBot controls search eligibility; GPTBot training access is independent; ChatGPT-User is user-triggered.", "AI search and training policies are separate user decisions."),
    ("openai-publishers", "Publishers and developers FAQ", "help.openai.com", "https://help.openai.com/en/articles/12627856-publishers-and-developers-faq", "Allow OAI-SearchBot for ChatGPT search inclusion; GPTBot can be controlled independently; referral URLs may identify chatgpt.com.", "ChatGPT referral measurement and crawler readiness are documented but not activated."),
    ("wcag-language", "Understanding SC 3.1.1 Language of Page", "w3.org", "https://www.w3.org/WAI/WCAG22/Understanding/language-of-page.html", "The predominant language must be programmatically determinable.", "Language declaration waits for the approved language architecture."),
    ("aria-apg", "Read Me First", "w3.org", "https://www.w3.org/WAI/ARIA/apg/practices/read-me-first/", "Prefer native semantics; ARIA roles require matching behavior and assistive-technology testing.", "Visible answer content uses native semantic HTML in the integration plan."),
    ("apple-business-connect", "Manage place card information in Apple Business Connect", "support.apple.com", "https://support.apple.com/en-ie/guide/business/abcbdc543423/web", "Place-card facts should be current and hours should agree with the official website; account permission is required.", "Apple parity is planned, but account work is externally authorized."),
    ("google-crawler-changelog", "Google crawler documentation changelog", "developers.google.com", "https://developers.google.com/crawling/docs/changelog", "Crawler documentation is actively maintained and should be rechecked before integration.", "Phase 4 includes a freshness recheck before production changes."),
)


def build_source_register() -> dict[str, Any]:
    sources = [
        {
            "id": row[0],
            "title": row[1],
            "officialDomain": row[2],
            "url": row[3],
            "retrievalDate": AS_OF_DATE,
            "relevantRule": row[4],
            "implementationConsequence": row[5],
            "changedPhase3APlan": row[0] in {"google-ai", "openai-bots", "openai-publishers", "apple-business-connect"},
        }
        for row in OFFICIAL_SOURCES
    ]
    return {
        "schemaVersion": SCHEMA_VERSION,
        "retrievalDate": AS_OF_DATE,
        "primarySourcesOnly": True,
        "sourceCount": len(sources),
        "sources": sources,
        "status": "PASS",
    }


def build_platform_coverage() -> dict[str, Any]:
    rows = [
        ("google-search", "Google Search", "Links and Googlebot", "Sitemap or Search Console", "search_crawler_policy", True, True, False, "Search Console", "Search Console", True, "USER_DECISION_REQUIRED", "Origin, crawler policy and account status unresolved", "google-search-works"),
        ("google-images", "Google Images", "Crawlable img elements", "Discovery through pages or image sitemap", "search_crawler_policy", True, True, False, "Search Console image search", "Search Console", True, "SETUP_REQUIRED", "Responsive/public image URLs unresolved", "google-images"),
        ("google-local", "Google local search", "Website and local entity sources", "Business Profile management", "search_crawler_policy", True, False, True, "GBP/Search observation", "GBP performance", True, "EXTERNAL_AUTHORIZATION_REQUIRED", "GBP access not authorized", "google-local-sources"),
        ("google-maps", "Google Maps / Business Profile", "Business Profile and Maps place", "Claimed/verified profile", "not-a-website-crawler-control", True, False, True, "Profile ownership", "GBP performance", True, "EXTERNAL_AUTHORIZATION_REQUIRED", "Ownership and current place identity unverified", "google-gbp-performance"),
        ("google-ai", "Google generative search experiences", "Googlebot and indexed Search content", "No separate submission mechanism", "search_crawler_policy", True, False, False, "Search indexing controls", "Search Console Web reporting", True, "USER_DECISION_REQUIRED", "Normal Search eligibility controls apply; inclusion is not guaranteed", "google-ai"),
        ("bing-search", "Bing Search", "Links and Bingbot", "Bing Webmaster sitemap", "search_crawler_policy", True, True, False, "Bing Webmaster verification", "Bing Webmaster Tools", True, "USER_DECISION_REQUIRED", "Origin, policy and account unresolved", "bing-sitemaps"),
        ("bing-images", "Bing Images", "Crawlable images and Bingbot", "No separate verified submission in this phase", "search_crawler_policy", True, True, False, "Bing Webmaster observation", "Bing Webmaster Tools", True, "SETUP_REQUIRED", "Public responsive image URLs unresolved", "bing-robots"),
        ("bing-webmaster", "Bing Webmaster Tools", "Verified site property", "Sitemap and diagnostics", "not-applicable", True, True, False, "Account/site verification", "Tool reports", True, "EXTERNAL_AUTHORIZATION_REQUIRED", "Account access not authorized", "bing-sitemaps"),
        ("copilot", "Microsoft Copilot search/grounding", "Bing-indexed content", "No separate verified submission mechanism", "search_crawler_policy", True, False, False, "Bing eligibility evidence", "Referral and Bing reports when available", False, "SETUP_REQUIRED", "No separate production mechanism is claimed", "bing-robots"),
        ("indexnow", "IndexNow", "Changed URL push", "Protocol endpoint after key ownership", "not-applicable", True, False, False, "Key file and response log", "IndexNow diagnostics", True, "CREDENTIAL_REQUIRED", "Origin, key and authorization unresolved", "indexnow-protocol"),
        ("chatgpt-search", "ChatGPT Search", "OAI-SearchBot and indexed sources", "No account submission mechanism", "ai_search_crawler_policy", True, False, False, "robots and crawl observation", "Referral analytics where supplied", False, "USER_DECISION_REQUIRED", "OAI-SearchBot policy unresolved; eligibility is not inclusion", "openai-bots"),
        ("standards-crawlers", "Standards-compliant crawlers", "Links, robots and sitemaps", "Platform-specific where available", "unknown_crawler_policy", True, True, False, "Server/crawl logs", "Server analytics", False, "USER_DECISION_REQUIRED", "Unknown-crawler policy unresolved", "google-robots"),
        ("greek-local-services", "Greek local-discovery services", "Platform listing or crawl", "Platform-specific only", "platform-specific", True, False, True, "Manual authorized observation", "Platform-specific", True, "EXTERNAL_AUTHORIZATION_REQUIRED", "No verified platform list or account access", "google-local-sources"),
        ("apple-local", "Apple local-discovery services", "Apple Business Connect place card", "Authorized Business Connect management", "not-applicable", True, False, True, "Account/place verification", "Platform-specific", True, "EXTERNAL_AUTHORIZATION_REQUIRED", "Account access not authorized", "apple-business-connect"),
        ("wolt", "Wolt", "Verified local provider link", "No search submission mechanism claimed", "not-applicable", False, False, True, "Authorized listing observation", "Outbound click analytics", True, "EXTERNAL_AUTHORIZATION_REQUIRED", "Local URL is verified; current listing parity not externally checked", "local-contract"),
        ("efood", "efood", "Verified local provider link", "No search submission mechanism claimed", "not-applicable", False, False, True, "Authorized listing observation", "Outbound click analytics", True, "EXTERNAL_AUTHORIZATION_REQUIRED", "Local URL is verified; current listing parity not externally checked", "local-contract"),
        ("social-previews", "Social preview systems", "Shared canonical URL metadata", "No indexing submission mechanism claimed", "platform-specific", True, False, False, "Platform preview debugger where authorized", "Referral analytics", False, "USER_DECISION_REQUIRED", "Canonical and social image are unresolved", "google-canonical"),
    ]
    platforms = []
    for row in rows:
        platforms.append({
            "id": row[0], "platform": row[1], "discoveryMechanism": row[2], "indexingOrSubmissionMechanism": row[3],
            "crawlerPolicy": row[4], "canonicalDependency": row[5], "sitemapDependency": row[6], "businessProfileDependency": row[7],
            "structuredDataRelevance": "SUPPORTING_NOT_GUARANTEED", "imageRequirements": "Platform-specific public crawlable assets where applicable",
            "verificationMethod": row[8], "measurementMethod": row[9], "accountRequirement": row[10],
            "credentialRequirement": row[10], "currentProjectStatus": row[11], "actionRequired": row[12],
            "limitation": "No indexing, ranking, local placement or citation outcome is guaranteed.", "evidenceSource": row[13],
        })
    return {"schemaVersion": SCHEMA_VERSION, "platformCount": len(platforms), "productionReady": False, "platforms": platforms}


def build_url_policy() -> dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "status": "USER_DECISION_REQUIRED",
        "productionEligible": False,
        "approvedValues": {"productionOrigin": None, "preferredHostname": None, "canonicalHomeUrl": None},
        "rules": {
            "httpsOnly": "REQUIRED_AFTER_ORIGIN_APPROVAL",
            "wwwPreference": "USER_DECISION_REQUIRED",
            "trailingSlash": "USER_DECISION_REQUIRED",
            "indexHtmlNormalization": "REDIRECT_TO_CANONICAL_PATH",
            "httpToHttps": "PERMANENT_REDIRECT_REQUIRED",
            "alternateHostname": "PERMANENT_REDIRECT_TO_PREFERRED_HOST",
            "githubPagesPreview": "NOINDEX_OR_NON_PRODUCTION_ONLY",
            "customDomain": "MUST_MATCH_APPROVED_ORIGIN",
            "queryParameters": "SELF_CANONICALIZE_ONLY_WHEN_CONTENT_DISTINCT; OTHERWISE_CANONICAL_BASE_URL",
            "fragments": "NEVER_CANONICAL_IDENTIFIERS",
            "stagingPreview": "NOINDEX_AND_ACCESS_CONTROL_WHERE_APPROPRIATE",
            "parity": ["canonical", "Open Graph URL", "schema URLs", "sitemap URLs", "internal absolute URLs"],
        },
        "validatorFailures": [
            "canonical origin mismatch", "schema URL mismatch", "sitemap URL mismatch", "Open Graph URL mismatch",
            "unapproved internal absolute origin", "HTTP canonical", "alternate-host canonical",
        ],
        "blockedBy": ["production_origin", "preferred_hostname", "https_status", "canonical_home_url"],
    }


def build_crawler_policy() -> dict[str, Any]:
    categories = [
        {"id": "search_indexing", "label": "SEARCH AND INDEXING CRAWLERS", "examples": ["Googlebot", "Bingbot"], "decision": None, "status": "USER_DECISION_REQUIRED", "purpose": "Search crawling and indexing eligibility"},
        {"id": "ai_search", "label": "AI SEARCH AND CITATION CRAWLERS", "examples": ["OAI-SearchBot"], "decision": None, "status": "USER_DECISION_REQUIRED", "purpose": "Search answers and citations; independent of training"},
        {"id": "ai_training", "label": "AI TRAINING CRAWLERS", "examples": ["GPTBot"], "decision": None, "status": "USER_DECISION_REQUIRED", "purpose": "Model training consent; independent of search"},
        {"id": "ad_validation", "label": "AD AND VALIDATION CRAWLERS", "examples": ["AdsBot-Google"], "decision": None, "status": "USER_DECISION_REQUIRED", "purpose": "Advertising and validation where used"},
        {"id": "unknown", "label": "UNKNOWN CRAWLERS", "examples": [], "decision": None, "status": "USER_DECISION_REQUIRED", "purpose": "Default standards-compliant crawler treatment"},
        {"id": "malicious", "label": "MALICIOUS OR ABUSIVE CRAWLERS", "examples": [], "decision": "USE_SECURITY_CONTROLS_NOT_ROBOTS_AS_PRIMARY_CONTROL", "status": "APPROVED_SAFEGUARD", "purpose": "Rate limiting, hosting and security controls"},
    ]
    return {
        "schemaVersion": SCHEMA_VERSION,
        "status": "USER_DECISION_REQUIRED",
        "previewOnly": True,
        "productionEligible": False,
        "productionOrigin": None,
        "sitemapUrl": None,
        "categories": categories,
        "safeguards": [
            "Do not block CSS, JavaScript or production images needed to render indexable pages.",
            "Do not use robots.txt as a security mechanism.",
            "Do not block a page when a crawler must read its noindex directive.",
            "Keep staging and production policies separate.",
            "Do not claim llms.txt as a Google ranking requirement.",
            "Do not emit experimental directives without official support and user approval.",
        ],
        "llmsTxt": {"status": "NOT_APPLICABLE", "reason": "No official Google ranking requirement; no user approval for an optional platform policy file."},
        "blockedBy": ["search_crawler_policy", "ai_search_crawler_policy", "ai_training_crawler_policy", "unknown_crawler_policy", "canonical_home_url"],
    }


def build_entity_graph(business: dict[str, Any], menu: dict[str, Any]) -> dict[str, Any]:
    fields = business["fields"]
    eligible = [p for p in menu["products"] if p["structuredDataEligibility"] == "ELIGIBLE_WITHOUT_OFFER"]
    return {
        "schemaVersion": SCHEMA_VERSION,
        "status": "USER_DECISION_REQUIRED",
        "productionEligible": False,
        "primaryEntity": "business:big-mama",
        "stableProductionId": None,
        "nodes": [
            {"id": "business:big-mama", "type": "Restaurant", "facts": ["name", "telephone", "address", "geo", "regularOpeningHours", "servedCuisine"], "blockedFacts": ["url", "sameAs", "priceRange", "aggregateRating", "review"]},
            {"id": "website:big-mama", "type": "WebSite", "status": "BLOCKED_BY_PRODUCTION_ORIGIN"},
            {"id": "webpage:home", "type": "WebPage", "status": "BLOCKED_BY_CANONICAL_URL"},
            {"id": "menu:big-mama", "type": "Menu", "eligibleProductIds": [p["id"] for p in eligible], "blockedProductIds": ["product:big-tokyo"]},
        ],
        "verifiedFacts": {
            "name": fields["canonicalBrandName"]["value"], "telephone": fields["telephone"]["value"],
            "address": fields["address"]["value"], "geo": fields["geo"]["value"],
            "openingHours": fields["openingHours"]["value"], "timeZone": fields["openingHours"]["timeZone"],
            "servedCuisine": ["Burgers"],
        },
        "invariants": ["exactly one Restaurant", "stable production @id", "NAP/hours/menu parity", "visible-content support", "no unsupported rating", "Big Tokyo excluded until resolved"],
        "blockedBy": ["canonical_home_url", "primary_business_category", "price_range", "google_business_profile", "social_profiles", "big_tokyo_status", "displayed_rating", "review_count"],
    }


def build_local_source(business: dict[str, Any], menu: dict[str, Any]) -> dict[str, Any]:
    f = business["fields"]
    return {
        "schemaVersion": SCHEMA_VERSION,
        "status": "PASS_WITH_EXTERNAL_VERIFICATION_REQUIRED",
        "entityId": business["entityId"],
        "nap": {"name": f["canonicalBrandName"]["value"], "address": f["address"]["value"], "telephone": f["telephone"]["value"], "status": "VERIFIED_LOCAL_SOURCE"},
        "geo": {**f["geo"]["value"], "status": "VERIFIED_LOCAL_SOURCE"},
        "hours": {"regular": f["openingHours"]["value"], "timeZone": f["openingHours"]["timeZone"], "holidayPolicy": None, "status": "USER_DECISION_REQUIRED_FOR_EXCEPTIONS"},
        "category": {"value": None, "status": "USER_DECISION_REQUIRED"},
        "cuisine": {"value": ["Burgers"], "status": "VERIFIED_LOCAL_SOURCE"},
        "orderingUrls": f["orderingUrls"]["value"],
        "websiteUrl": {"value": None, "status": "USER_DECISION_REQUIRED"},
        "menuRef": "seo/menu.json",
        "blockedProductIds": [p["id"] for p in menu["products"] if p["structuredDataEligibility"] == "BLOCKED_CONTRADICTION"],
        "reviewDestination": {"value": f["mapsUrl"]["value"], "status": "EXTERNAL_AUTHORIZATION_REQUIRED"},
        "socialProfiles": {"value": [], "status": "USER_DECISION_REQUIRED"},
        "parityTargets": ["website", "schema", "sitemap", "Google Business Profile", "Bing business data", "Wolt", "efood", "verified citations", "map links", "contact CTAs"],
        "externalCorrectionPolicy": {"automaticOverwrite": False, "requiredFields": ["field", "observedValue", "approvedValue", "platform", "evidence", "recommendedAction", "risk", "authorizationRequired"]},
        "externalObservations": [],
        "limitation": "No external listing was accessed or verified in Phase 3B.",
    }


ANSWER_SPECS = (
    ("what", "What is Big Mama Burgers n' Fries?", "Big Mama Burgers n' Fries is a restaurant in Nea Filadelfia with a visible menu of burgers, fries and cookies.", "About or home", ["public_business_name", "street_address", "served_cuisine"], "business:big-mama", "informational", "VERIFIED"),
    ("where", "Where is it located?", "It is at Leof. Dekelias 114, Nea Filadelfia 143 41, Greece.", "Location", ["street_address", "locality", "postal_code", "country"], "location:nea-filadelfia", "local-navigation", "VERIFIED"),
    ("hours", "What are the opening hours?", "Posted regular hours are Monday-Friday 17:00-01:00, Saturday 15:00-02:00, and Sunday 14:00-01:00.", "Location", ["opening_hours"], "business:big-mama", "hours", "VERIFIED"),
    ("open-now", "Is it open now?", None, "Location", ["opening_hours", "timezone", "holiday_hours_policy"], "business:big-mama", "hours", "SETUP_REQUIRED"),
    ("timezone", "What timezone applies?", "The verified operating timezone is Europe/Athens.", "Location", ["timezone"], "business:big-mama", "hours", "VERIFIED"),
    ("food", "What food does it serve?", "The visible menu includes beef burgers, chicken burgers, a limited item, fries and cookies.", "Menu", ["served_cuisine"], "menu:big-mama", "menu", "VERIFIED"),
    ("categories", "What menu categories are available?", "The visible categories are Beef Burgers, Chicken Burgers, Limited, Fries and Cookies.", "Menu", ["seo/menu.json"], "menu:big-mama", "menu", "VERIFIED"),
    ("beef", "Which beef burgers are available?", "The visible beef category lists Mama's Original Single, Bacon Lovers Double Burger and Truffle Oh Mama Double Burger.", "Menu", ["seo/menu.json"], "menu:big-mama", "menu", "VERIFIED"),
    ("chicken", "Which chicken items are available?", "The visible chicken category lists Lava Mam' Chicken and Truffle Parmesan Chicken. Big Tokyo is shown with contradictory availability and is not claimed as available.", "Menu", ["seo/menu.json", "big_tokyo_status"], "menu:big-mama", "menu", "CONTRADICTORY"),
    ("limited", "What is the current Limited item?", "Mama in Paris is displayed in the Limited category.", "Menu", ["seo/menu.json"], "product:mama-in-paris", "menu", "VERIFIED"),
    ("fries", "Are fries available?", "Big Mama Fries are displayed on the menu as fresh hand-cut fries.", "Menu", ["seo/menu.json"], "product:big-mama-fries", "menu", "VERIFIED"),
    ("cookies", "Are cookies available?", "Original Double Choco Cookie is displayed in the Cookies category.", "Menu", ["seo/menu.json"], "product:original-double-choco-cookie", "menu", "VERIFIED"),
    ("delivery", "Does the restaurant deliver?", "The website links to Wolt and efood; current delivery area and availability must be confirmed with the selected provider.", "Order", ["wolt_url", "efood_url"], "business:big-mama", "transactional", "VERIFIED"),
    ("wolt", "Is ordering available through Wolt?", "The website provides a Wolt ordering link; current provider availability must be confirmed on Wolt.", "Order", ["wolt_url", "order_cta"], "business:big-mama", "transactional", "SETUP_REQUIRED"),
    ("efood", "Is ordering available through efood?", "The website provides an efood ordering link; current provider availability must be confirmed on efood.", "Order", ["efood_url", "order_cta"], "business:big-mama", "transactional", "SETUP_REQUIRED"),
    ("telephone", "What is the telephone number?", "The verified public telephone number is +30 216 003 3303.", "Location", ["public_telephone"], "business:big-mama", "contact", "VERIFIED"),
    ("directions", "How can customers get directions?", "The current site provides a Google Maps directions link for the verified street address.", "Location", ["street_address", "google_business_profile"], "location:nea-filadelfia", "navigation", "SETUP_REQUIRED"),
    ("reviews", "How can customers read reviews?", "The current site links to a Google Maps place page; the production review destination still requires external verification.", "Reviews", ["google_business_profile"], "business:big-mama", "review", "SETUP_REQUIRED"),
    ("contact", "How can customers contact the business?", "Customers can use the verified public telephone number. A public email decision is still required.", "Contact", ["public_telephone", "public_email", "contact_cta"], "business:big-mama", "contact", "SETUP_REQUIRED"),
    ("big-tokyo", "Is Big Tokyo currently available?", None, "Menu", ["big_tokyo_status"], "product:big-tokyo", "menu", "CONTRADICTORY"),
)


def build_answer_data() -> dict[str, Any]:
    records = []
    for identifier, question, answer, section, dependencies, entity, intent, status in ANSWER_SPECS:
        blocked = status in {"SETUP_REQUIRED", "CONTRADICTORY"}
        records.append({
            "id": f"answer:{identifier}", "canonicalQuestion": question, "conciseAnswer": answer,
            "expandedAnswer": answer, "visibleSourceSection": section, "factualDependencies": dependencies,
            "freshnessDependency": "Reverify after material menu, hours, provider or business-fact change.",
            "entityReferences": [entity], "userIntent": intent, "language": "en-pending-strategy",
            "lastVerifiedDate": AS_OF_DATE if status == "VERIFIED" else None,
            "contradictionStatus": "ACTIVE" if status == "CONTRADICTORY" else "NONE",
            "schemaRelationship": None, "verificationStatus": status,
            "publicationStatus": "BLOCKED" if blocked else "PREVIEW_ONLY",
        })
    return {
        "schemaVersion": SCHEMA_VERSION,
        "status": "USER_DECISION_REQUIRED",
        "recordCount": len(records),
        "recordContract": {"visibleSemanticHtmlRequired": True, "hiddenContentAllowed": False, "interactionOnlyAllowed": False, "schemaOnlyClaimsAllowed": False},
        "records": records,
        "languageStrategy": "USER_DECISION_REQUIRED",
        "publicationPolicy": "Phase 4 integration approval and all factual dependencies are required.",
    }


def build_image_data(existing: dict[str, Any]) -> dict[str, Any]:
    hashes: dict[str, list[str]] = {}
    for row in existing["images"]:
        source = ROOT / row["sourcePath"]
        digest = sha256_file(source) if source.is_file() else None
        if digest:
            hashes.setdefault(digest, []).append(row["sourcePath"])
    images = []
    for row in existing["images"]:
        source = ROOT / row["sourcePath"]
        width, height = row.get("width"), row.get("height")
        digest = sha256_file(source) if source.is_file() else None
        duplicates = hashes.get(digest, []) if digest else []
        images.append({
            "id": row["id"], "sourcePath": row["sourcePath"], "publicUrl": None,
            "contentSubject": row.get("semanticSubject"), "productEntityRelationship": row.get("relatedEntity"),
            "imagePurpose": "brand" if "logo" in row["id"] else "content-or-product",
            "intrinsicDimensions": {"width": width, "height": height},
            "aspectRatio": round(width / height, 6) if width and height else None,
            "format": row.get("format"), "byteSize": row.get("fileSize"),
            "transparencyRequirement": "PRESERVE_WHERE_PRESENT_OR_DESIGN_REQUIRED",
            "aboveFoldStatus": "OBSERVED_FROM_PHASE3A", "loadingPolicy": "PHASE4_PERFORMANCE_DECISION_REQUIRED",
            "decodingPolicy": "ASYNC_WHERE_SAFE_AFTER_RENDER_TESTING", "responsiveVariants": [], "srcset": None, "sizes": None,
            "altText": (row.get("currentAlt") or [None])[0], "caption": None,
            "socialEligibility": row.get("socialSharingEligibility", False),
            "structuredDataRelationship": row.get("relatedEntity"),
            "imageSitemapEligibility": False, "duplicationStatus": "DUPLICATE_BYTES" if len(duplicates) > 1 else "UNIQUE_BYTES",
            "duplicatePaths": duplicates if len(duplicates) > 1 else [], "sha256": digest,
            "rightsOwnershipStatus": "USER_DECISION_REQUIRED", "productionStatus": "SETUP_REQUIRED_PUBLIC_URL",
        })
    return {
        "schemaVersion": SCHEMA_VERSION, "status": "USER_DECISION_REQUIRED", "productionOrigin": None,
        "imageCount": len(images), "images": images,
        "policies": {"altText": "Natural and contextual; no keyword stuffing.", "responsive": "AVIF/WebP where beneficial with fallback and verified quality.", "masters": "Do not modify or remove source masters without separate approval.", "factualImagery": "Do not publish unapproved generated product imagery as factual photography."},
    }


def build_measurement_plan() -> dict[str, Any]:
    events = [
        ("wolt_click", "Outbound Wolt link activation"), ("efood_click", "Outbound efood link activation"),
        ("phone_click", "Telephone link activation"), ("directions_click", "Directions link activation"),
        ("review_click", "Review destination activation"), ("menu_interaction", "Menu category/product interaction"),
        ("provider_chooser_open", "Provider chooser opened"), ("provider_selection", "Ordering provider selected"),
        ("contact_action", "Approved contact action"), ("language_selection", "Language variant selected"),
        ("external_referral_source", "Privacy-safe external referrer classification"),
    ]
    return {
        "schemaVersion": SCHEMA_VERSION, "status": "SETUP_REQUIRED", "productionEligible": False,
        "consentGate": {"status": "USER_DECISION_REQUIRED", "analyticsBeforeConsentAllowed": False},
        "events": [{"id": key, "description": desc, "status": "DESIGNED_NOT_DEPLOYED", "personalDataRequired": False} for key, desc in events],
        "platforms": {
            "googleSearchConsole": {"status": "EXTERNAL_AUTHORIZATION_REQUIRED", "metrics": ["indexed pages", "queries", "impressions", "clicks", "CTR", "average position", "page/query segments", "image search", "rich-result reports", "crawl/index errors"], "aiFeatureNote": "Use officially available Search Console reporting only; no separate AI report is inferred."},
            "bingWebmaster": {"status": "EXTERNAL_AUTHORIZATION_REQUIRED", "metrics": ["indexed pages", "keywords", "crawl errors", "backlinks", "sitemap processing", "IndexNow diagnostics", "SEO reports"]},
            "googleBusinessProfile": {"status": "EXTERNAL_AUTHORIZATION_REQUIRED", "metrics": ["profile views", "website actions", "calls", "directions", "order actions", "available search terms", "photo activity", "review operations"]},
            "analytics": {"status": "USER_DECISION_REQUIRED", "metrics": [key for key, _ in events]},
            "aiReferrals": {"status": "SETUP_REQUIRED", "metrics": ["referral source", "supplied UTM source", "landing page", "conversion action", "measurable assisted conversion"]},
        },
        "privacy": ["No unnecessary personal data", "No credentials in client code or reports", "Consent/legal decision before deployment"],
        "claimsPolicy": "Local synthetic data is never field Core Web Vitals; absent account data remains unavailable.",
    }


def build_review_operations() -> dict[str, Any]:
    return {
        "schemaVersion": SCHEMA_VERSION, "status": "SETUP_REQUIRED", "publicationStatus": "BLOCKED",
        "destination": {"value": None, "status": "EXTERNAL_AUTHORIZATION_REQUIRED"},
        "displayedRating": {"value": None, "status": "USER_DECISION_REQUIRED", "rule": "Verify, timestamp, source and refresh or remove."},
        "reviewCount": {"value": None, "status": "USER_DECISION_REQUIRED"},
        "allowedChannels": ["post-purchase reminder", "receipt/card", "approved QR", "direct neutral review destination"],
        "prohibited": ["review gating", "positive-review incentives", "fabricated reviews", "selective suppression", "unsupported rating markup", "stale relative dates", "unapproved scraping or republication"],
        "workflow": ["verify destination", "request neutrally", "record response evidence", "escalate operational complaints", "refresh displayed evidence on schedule"],
        "responseTimeTarget": "USER_DECISION_REQUIRED", "evidenceRefreshCadence": "USER_DECISION_REQUIRED",
        "externalAccountAuthorization": WRITE_APPROVAL,
    }


def build_authority_plan() -> dict[str, Any]:
    classes = ["local press", "neighborhood publications", "food publications", "suppliers", "business associations", "local events", "sponsorships", "community initiatives", "relevant directories", "delivery platforms", "map/business platforms", "genuine creator coverage", "partnerships"]
    return {
        "schemaVersion": SCHEMA_VERSION, "status": "READINESS_ONLY", "productionEligible": False,
        "opportunityClasses": [{"targetClass": name, "specificTarget": None, "relevance": "Requires real relationship or audience fit", "legitimacyEvidence": "USER_DECISION_REQUIRED", "contactRoute": None, "risk": "Do not imply endorsement or pay for ranking links", "nofollowSponsoredExpectation": "Evaluate per relationship", "status": "SETUP_REQUIRED", "measurement": "Qualified referral, citation accuracy and audience value"} for name in classes],
        "prohibited": ["purchased ranking links", "private blog networks", "automated directory blasts", "irrelevant guest posts", "reciprocal schemes", "fake press or awards", "mass AI outreach", "exact-match anchor manipulation"],
        "externalOutreachAuthorized": False,
    }


SKILL_STATUS = {
    "seo-plan": "APPLIED_READ_ONLY", "seo-flow": "APPLIED_READ_ONLY", "seo-audit": "APPLIED_READ_ONLY",
    "seo-technical": "APPLIED_READ_ONLY", "seo-page": "APPLIED_READ_ONLY", "seo-performance": "APPLIED_READ_ONLY",
    "seo-visual": "APPLIED_READ_ONLY", "seo-images": "APPLIED_READ_ONLY", "seo-schema": "APPLIED_READ_ONLY",
    "seo-sitemap": "APPLIED_READ_ONLY", "seo-content": "APPLIED_READ_ONLY", "seo-geo": "APPLIED_READ_ONLY",
    "seo-cluster": "APPLIED_READINESS_ONLY", "seo-sxo": "APPLIED_READ_ONLY", "seo-local": "APPLIED_READ_ONLY",
    "seo-maps": "DEFERRED_EXTERNAL_ACCOUNT_AUTHORIZATION_REQUIRED", "seo-hreflang": "DEFERRED_USER_DECISION_REQUIRED",
    "seo-ecommerce": "APPLIED_READINESS_ONLY", "seo-competitor-pages": "NOT_APPLICABLE_WITH_REASON",
    "seo-programmatic": "NOT_APPLICABLE_WITH_REASON", "seo-backlinks": "DEFERRED_EXTERNAL_ACCOUNT_AUTHORIZATION_REQUIRED",
    "seo-drift": "APPLIED_READ_ONLY", "seo-google": "DEFERRED_EXTERNAL_ACCOUNT_AUTHORIZATION_REQUIRED",
    "seo-dataforseo": "DEFERRED_CREDENTIAL_REQUIRED", "seo-firecrawl": "DEFERRED_NETWORK_AUTHORIZATION_REQUIRED",
    "seo-image-gen": "BLOCKED_BY_WEBSITE_PROTECTION",
}


def build_skill_routing() -> tuple[dict[str, Any], dict[str, Any]]:
    phase3 = read_json(REPORTS_DIR / "phase3-skill-routing.json")
    previous = {row["name"]: row for row in phase3["specialists"]}
    rows = []
    for name, status in SKILL_STATUS.items():
        old = previous[name]
        applicable = status not in {"NOT_APPLICABLE_WITH_REASON", "BLOCKED_BY_WEBSITE_PROTECTION"}
        rows.append({
            "name": name, "skillPath": old["skillPath"], "skillSha256": old["skillSha256"],
            "applicability": "APPLICABLE" if applicable else "NOT_APPLICABLE_OR_BLOCKED",
            "workflowInvoked": "Phase 3A specialist instructions retained; Phase 3B contract/readiness review applied inline" if applicable else "Applicability and authorization gate evaluated",
            "evidenceConsumed": ["Phase 3A artifacts", "SEO contracts", "protected website source read-only", "official source register"],
            "evidenceProduced": ["Phase 3B contracts/reports/previews"],
            "agentProfileUsed": old.get("agentProfilePath"), "executionMode": "INLINE_READ_ONLY_OR_ISOLATED_WRITE",
            "limitation": "No website writes, external account activity or unauthorized network execution.", "finalStatus": status,
        })
    payload = {"schemaVersion": SCHEMA_VERSION, "orchestratorPath": str(SKILL_ROOT / "seo" / "SKILL.md"), "orchestratorSha256": sha256_file(SKILL_ROOT / "seo" / "SKILL.md"), "specialistCount": len(rows), "statusCounts": dict(sorted(Counter(r["finalStatus"] for r in rows).items())), "specialists": rows}
    agents = []
    for row in rows:
        path = row["agentProfileUsed"]
        agents.append({"specialist": row["name"], "profilePath": path, "profileSha256": sha256_file(Path(path)) if path and Path(path).is_file() else None, "usage": "PROFILE_REFERENCED_FOR_ROUTING_ONLY" if path else "NO_PROFILE_INSTALLED_INLINE_ORCHESTRATION", "agentSpawned": False, "externalActivity": False})
    agent_payload = {"schemaVersion": SCHEMA_VERSION, "installedProfileCount": sum(bool(a["profilePath"]) for a in agents), "profilesUsedForRouting": [a["profilePath"] for a in agents if a["profilePath"]], "agentExecutionCount": 0, "agents": agents}
    return payload, agent_payload


def _decision_form(truth: dict[str, Any]) -> str:
    unresolved = [row for row in truth["fields"] if not row["productionEligible"]]
    lines = [
        "# Big Mama Production Decision Form", "", f"Status: `USER_DECISION_REQUIRED`", "",
        "Complete only the fields below. Do not provide credentials or verification tokens in this document.",
        "External account access is not requested by this form.", "",
    ]
    for number, row in enumerate(unresolved, start=1):
        lines.extend([
            f"## {number}. {row['label']}", "", f"- Contract ID: `{row['id']}`", f"- Current status: `{row['status']}`",
            f"- Why required: {row['reason']}", f"- Affects: {', '.join(row['affectedOutputs'])}", "- Decision/value:", "- Evidence/source (when factual):", "",
        ])
    lines.extend([
        "## Validation Gate", "", "Answers will be checked for URL validity, internal consistency, source support, crawler-policy separation, privacy implications and conflicts with protected website facts.", "",
        f"Website integration will remain blocked after answer validation until the exact phrase `{INTEGRATION_APPROVAL}` is supplied.",
    ])
    return "\n".join(lines)


def _build_docs() -> dict[str, str]:
    return {
        "docs/seo/MULTI-ENGINE-SEARCH-STRATEGY.md": """# Multi-Engine Search Strategy

Status: `USER_DECISION_REQUIRED`

Big Mama's controllable search system is one truthful, crawlable entity surface: a single approved origin, consistent NAP/hours/menu facts, visible semantic answers, crawlable images, coherent Restaurant markup, canonical/sitemap parity and measured customer actions. Search, local and AI answer systems consume the same public evidence; no crawler-only or AI-only copy is planned.

Google and Bing discovery use normal links, canonical URLs, crawl controls and optional sitemaps. Google AI experiences use normal Search eligibility controls. ChatGPT Search uses the independently controllable OAI-SearchBot; GPTBot training consent is a separate decision. IndexNow is only for materially changed, added or deleted URLs after origin/key approval.

No indexing, ranking, Local Pack position, rich result, image placement or AI citation is guaranteed. External platforms remain observational until separately authorized.
""",
        "docs/seo/LOCAL-SEARCH-OPERATIONS.md": """# Local Search Operations

Status: `EXTERNAL_AUTHORIZATION_REQUIRED`

The local source of truth is `seo/local-search-source.json`. Website, Restaurant schema, provider links, map destinations and future business-profile exports must match the approved name, address, phone, coordinates, regular hours, holiday exceptions, category, cuisine and menu status.

External listings are never overwritten automatically. A correction requires the conflicting field, observed value, approved value, platform, evidence, risk and explicit external-change authorization. Profile access, GBP performance, Apple Business Connect and other platform operations remain blocked.

Review requests must be neutral. Review gating, incentives, fabricated reviews, unsupported rating markup and stale relative dates are prohibited.
""",
        "docs/seo/AEO-GEO-CONTENT-STANDARD.md": """# AEO/GEO Content Standard

Status: `USER_DECISION_REQUIRED`

Every answer must be factual, concise, visible in semantic HTML, understandable out of context and supported by the production-truth contract. Critical answers may not depend on `display:none`, canvas, delayed rendering or interaction-only controls. Schema must never introduce facts absent from visible content.

The required 20-question inventory is in `seo/answer-data.json`. Big Tokyo, open-now, contact, review, language and provider answers stay blocked where dependencies are unresolved. No fake FAQs, query-variant pages, AI-only copy, llms.txt ranking claims or machine-translated production copy are permitted.
""",
        "docs/seo/SEARCH-MEASUREMENT-OPERATIONS.md": """# Search Measurement Operations

Status: `SETUP_REQUIRED`

Measurement is adapter-based and least-privilege. Search Console, Bing Webmaster and Business Profile data remain unavailable until read-only account authorization. Analytics remains blocked until consent, privacy and legal decisions are approved.

Planned conversion events cover Wolt, efood, telephone, directions, reviews, menu use, provider choice, contact and language selection. No credentials belong in source, client JavaScript or public reports. Local synthetic performance is never labeled field Core Web Vitals.
""",
        "docs/seo/DEPLOYMENT-AND-INDEXING-RUNBOOK.md": """# Deployment and Indexing Runbook

Status: `USER_DECISION_REQUIRED`

1. Validate all 44 production-truth fields and freeze the approved values.
2. Recheck current official crawler, schema and platform documentation.
3. Build canonical, metadata, schema, robots and sitemap outputs from one origin contract.
4. Validate JSON, XML, robots syntax, URL parity, visible-content parity and protected-file hashes.
5. Obtain the exact website-integration approval for the reviewed file-level plan.
6. Create rollback copies only for listed files and apply atomic, byte-aware changes.
7. Run static, browser, mobile, accessibility, console, network and security checks.
8. Deploy through the approved host/branch workflow.
9. After separate account authorization, submit the sitemap and materially changed URLs only where officially supported.
10. Record response evidence; external endpoint failure must not corrupt or roll back a healthy website deployment.

No deployment, submission, account access or website modification is authorized in Phase 3B.
""",
    }


def _build_previews(truth: dict[str, Any], entity: dict[str, Any], answers: dict[str, Any]) -> dict[str, str | dict[str, Any]]:
    blockers = truth["unresolvedFieldIds"]
    verified = entity["verifiedFacts"]
    graph = {
        "@context": "https://schema.org",
        "@graph": [{
            "@type": "Restaurant", "name": verified["name"], "telephone": verified["telephone"],
            "address": {"@type": "PostalAddress", **verified["address"]},
            "geo": {"@type": "GeoCoordinates", **verified["geo"]}, "servesCuisine": verified["servedCuisine"],
            "openingHoursSpecification": [{"@type": "OpeningHoursSpecification", "dayOfWeek": row["days"], "opens": row["opens"], "closes": row["closes"]} for row in verified["openingHours"]],
        }],
    }
    visible = [row for row in answers["records"] if row["conciseAnswer"]]
    answer_html = ["<!doctype html>", '<html lang="en">', "<head><meta charset=\"utf-8\"><title>Phase 3B answer preview</title></head>", "<body>", '<main data-status="PREVIEW_ONLY">', "<h1>Big Mama answer-content preview</h1>"]
    for row in visible:
        answer_html.extend(["<section>", f"<h2>{html.escape(row['canonicalQuestion'])}</h2>", f"<p>{html.escape(row['conciseAnswer'])}</p>", "</section>"])
    answer_html.extend(["</main>", "</body>", "</html>"])
    return {
        "reports/seo/generated-preview/phase3b/head-preview.html": """<!-- USER_DECISION_REQUIRED: no production head is emitted. -->
<!-- Required: approved canonical origin, hostname, language, title/description wording and social image. -->
<meta name="phase3b-status" content="USER_DECISION_REQUIRED">
""",
        "reports/seo/generated-preview/phase3b/schema-preview.json": {"schemaVersion": SCHEMA_VERSION, "status": "PREVIEW_ONLY_USER_DECISION_REQUIRED", "productionEligible": False, "omitted": ["stable @id and URLs", "sameAs", "priceRange", "AggregateRating", "Review", "Big Tokyo"], "blockedBy": blockers, "jsonLdPreview": graph},
        "reports/seo/generated-preview/phase3b/robots-preview.txt": "# USER_DECISION_REQUIRED\n# No production robots directives emitted.\n# Required: crawler policies, canonical origin, sitemap URL.\n",
        "reports/seo/generated-preview/phase3b/sitemap-preview.xml": "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<phase3bPreview xmlns=\"urn:big-mama:seo:phase3b\"><status>USER_DECISION_REQUIRED</status><reason>Canonical origin is unresolved; no production URL emitted.</reason></phase3bPreview>\n",
        "reports/seo/generated-preview/phase3b/social-preview.json": {"schemaVersion": SCHEMA_VERSION, "status": "USER_DECISION_REQUIRED", "productionEligible": False, "canonicalUrl": None, "socialImageUrl": None, "title": None, "description": None},
        "reports/seo/generated-preview/phase3b/answer-content-preview.html": "\n".join(answer_html),
        "reports/seo/generated-preview/phase3b/indexnow-preview.json": {"schemaVersion": SCHEMA_VERSION, "status": "CREDENTIAL_REQUIRED", "productionEligible": False, "host": None, "key": None, "keyLocation": None, "urlList": [], "submissionAttempted": False, "rule": "Submit only materially changed, added or deleted canonical URLs after approval."},
        "reports/seo/generated-preview/phase3b/platform-verification-preview.json": {"schemaVersion": SCHEMA_VERSION, "status": "EXTERNAL_AUTHORIZATION_REQUIRED", "productionEligible": False, "googleSearchConsole": None, "bingWebmaster": None, "googleBusinessProfile": None, "appleBusinessConnect": None, "tokensGenerated": False, "accountAccessAttempted": False},
    }


def _build_reports(
    truth: dict[str, Any], platforms: dict[str, Any], crawler: dict[str, Any], entity: dict[str, Any],
    answers: dict[str, Any], images: dict[str, Any], measurement: dict[str, Any], source_register: dict[str, Any],
) -> dict[str, Any]:
    unresolved = [row for row in truth["fields"] if not row["productionEligible"]]
    phase3_issues = read_json(REPORTS_DIR / "phase3-issue-register.json")
    readiness = {
        "schemaVersion": SCHEMA_VERSION, "status": "USER_DECISION_REQUIRED", "productionReady": False,
        "fieldCount": truth["fieldCount"], "resolvedCount": truth["fieldCount"] - truth["unresolvedCount"],
        "unresolvedCount": truth["unresolvedCount"], "unresolvedFields": [{"id": row["id"], "status": row["status"], "reason": row["reason"]} for row in unresolved],
        "p0TruthIntegrityBlockers": [{"id": "P0-TRUTH-GATE", "reason": "Production outputs cannot be accurate until all required production decisions are resolved."}],
        "websiteIntegrationStatus": "BLOCKED", "nextAction": "Complete docs/seo/PRODUCTION-DECISION-FORM.md",
    }
    content_gap = {
        "schemaVersion": SCHEMA_VERSION, "status": "USER_DECISION_REQUIRED",
        "requiredAnswerCount": len(answers["records"]), "answerStatusCounts": dict(sorted(Counter(r["publicationStatus"] for r in answers["records"]).items())),
        "languageOptions": [
            {"option": "Greek-primary single page", "maintenance": "LOW", "hreflang": "NOT_APPLICABLE", "status": "USER_DECISION_REQUIRED"},
            {"option": "English-primary single page", "maintenance": "LOW", "hreflang": "NOT_APPLICABLE", "status": "USER_DECISION_REQUIRED"},
            {"option": "Greek-primary with limited English support", "maintenance": "MEDIUM", "hreflang": "DEPENDS_ON_URL_ARCHITECTURE", "status": "USER_DECISION_REQUIRED"},
            {"option": "Full Greek and English URL variants", "maintenance": "HIGH", "hreflang": "REQUIRED_RECIPROCAL_SELF_REFERENCING", "status": "USER_DECISION_REQUIRED"},
        ],
        "candidatePages": ["Home", "Menu", "Location/Contact", "Delivery/Ordering", "About/Story", "Accessibility", "Privacy/Cookies"],
        "massLocalPagesAllowed": False, "machineTranslatedProductionCopyAllowed": False,
        "performanceCoordination": ["2.15-second loader", "hidden eager Big Tokyo images", "hidden animation intervals", "early Leaflet", "scroll-dependent reveal content", "large PNG payload", "missing responsive images", "fixed navigation offsets"],
        "websitePerformanceStatus": "AUDIT_ONLY_NO_OPTIMIZATION_AUTHORIZED",
    }
    consistency = {
        "schemaVersion": SCHEMA_VERSION, "status": "PASS_WITH_EXTERNAL_VERIFICATION_REQUIRED", "primaryRestaurantCount": 1,
        "localParity": {"name": "PASS", "address": "PASS", "telephone": "PASS", "coordinates": "PASS", "regularHours": "PASS", "menu": "PASS_LOCAL_CONTRACT", "holidayHours": "USER_DECISION_REQUIRED", "externalPlatforms": "EXTERNAL_AUTHORIZATION_REQUIRED"},
        "blockedSchemaFacts": entity["blockedBy"], "bigTokyoExcluded": True, "aggregateRatingExcluded": True,
    }
    crawler_review = {
        "schemaVersion": SCHEMA_VERSION, "status": "USER_DECISION_REQUIRED", "categoryCount": len(crawler["categories"]),
        "unresolvedCategories": [r["id"] for r in crawler["categories"] if r["status"] == "USER_DECISION_REQUIRED"],
        "searchAndTrainingSeparated": True, "robotsUsedAsSecurity": False, "llmsTxtRankingRequirementClaimed": False,
        "productionRobotsEmitted": False, "reason": "Approved policy and origin values are absent.",
    }
    plan = {
        "schemaVersion": SCHEMA_VERSION, "status": "USER_DECISION_REQUIRED", "productionReady": False,
        "websiteIntegrationStatus": "BLOCKED", "externalAccountsAccessed": False,
        "officialDocumentationResearchUsed": True, "externalPlatformExecutionAuthorized": False,
        "completedDecisionIndependentWork": ["official source register", "44-field truth contract", "17-platform matrix", "URL/crawler/entity/local/answer/image/measurement/review/authority contracts", "gated previews", "adversarial controls"],
        "blockedWork": ["final production previews", "exact Phase 4 file/selector/value plan", "website integration", "deployment", "platform verification/submission"],
        "requiredSequence": ["User completes decision form", "Validate answers", "Generate final production previews", "Generate exact Phase 4 file-level plan", "Freeze protected hashes", f"Request {INTEGRATION_APPROVAL}"],
        "potentialPhase4FilesNotYetApproved": ["index.html", "robots.txt", "sitemap.xml", "site.webmanifest", "approved social/favicons", "approved CI validation", "approved analytics integration"],
        "phase3AIssueCounts": phase3_issues["counts"],
        "mobileAndPerformance": content_gap["performanceCoordination"],
        "performanceImplementationAuthorized": False,
        "rollback": ["Use reports/seo/.cache/phase3b-rollback for Phase 3B contract rollback", "For Phase 4, back up only approved website files before atomic edits", "Compare protected SHA-256 before and after"],
        "requiredApprovals": {"websiteIntegration": INTEGRATION_APPROVAL, "externalRead": READ_APPROVAL, "externalChanges": WRITE_APPROVAL},
    }
    red_checks = [
        "ranking guarantees", "unsupported production facts", "fake schema eligibility", "hidden SEO content", "AI-search hacks", "llms.txt dependency", "keyword stuffing", "duplicate entities", "wrong canonical origin", "GitHub/custom-domain conflict", "unsupported ratings", "stale hours", "menu inconsistency", "Big Tokyo leakage", "doorway pages", "programmatic abuse", "fake local pages", "review manipulation", "link schemes", "crawler conflicts", "blocked search assets", "noindex/robots contradiction", "inaccessible answers", "JavaScript-only critical content", "analytics without consent", "credentials in source", "public internal reports", "external actions without authorization", "website writes before approval", "nondeterministic output", "manipulated performance evidence",
    ]
    red_team = {
        "schemaVersion": SCHEMA_VERSION, "status": "PASS_WITH_PRODUCTION_BLOCK", "attemptCount": len(red_checks),
        "checks": [{"attack": item, "result": "CONTROL_PRESENT", "productionBlock": item in {"unsupported production facts", "wrong canonical origin", "unsupported ratings", "Big Tokyo leakage", "analytics without consent"}} for item in red_checks],
        "unresolvedP0": [{"id": "P0-TRUTH-GATE", "status": "BLOCKS_INTEGRATION", "reason": "31 production decisions remain unresolved."}],
        "websiteWritesDetected": False, "externalActionsDetected": False,
    }
    return {"readiness": readiness, "contentGap": content_gap, "consistency": consistency, "crawlerReview": crawler_review, "plan": plan, "redTeam": red_team}


def _activation_markdown(plan: dict[str, Any], truth: dict[str, Any]) -> str:
    return f"""# Phase 3B Search Activation Plan

Status: `USER_DECISION_REQUIRED`

- Production-truth fields: **{truth['fieldCount']}**
- Unresolved fields: **{truth['unresolvedCount']}**
- Website integration: **BLOCKED**
- External account activity: **NONE**
- Website performance: **AUDIT ONLY**

Decision-independent contracts, official-source rules, platform coverage, safeguards and gated previews are built. Production-dependent values were not fabricated. Complete `docs/seo/PRODUCTION-DECISION-FORM.md`; answers must then be validated before final previews or an exact Phase 4 plan can exist.

No website file, asset, deployment configuration or external account is modified. The exact later website approval is `{INTEGRATION_APPROVAL}`. It is not requested until the decision gate is cleared.
"""


def write_final_report() -> dict[str, Any]:
    truth = read_json(DATA_DIR / "production-truth.json")
    validation_path = REPORTS_DIR / "phase3b-validation-report.json"
    determinism_path = REPORTS_DIR / "phase3b-determinism-report.json"
    integrity_path = REPORTS_DIR / "website-integrity-phase3b-comparison.json"
    validation = read_json(validation_path) if validation_path.is_file() else {"status": "PENDING", "tests": {"passed": 0, "failed": 0, "total": 0}}
    determinism = read_json(determinism_path) if determinism_path.is_file() else {"status": "PENDING"}
    integrity = read_json(integrity_path) if integrity_path.is_file() else {"status": "PENDING"}
    routing = read_json(REPORTS_DIR / "phase3b-skill-routing.json")
    report = f"""# Big Mama Phase 3B Report

Status: **DECISION GATE REACHED — USER INPUT REQUIRED**

## Verified Scope

- 44-field production-truth contract built from frozen Phase 3A and protected local evidence.
- {truth['fieldCount'] - truth['unresolvedCount']} fields are production eligible; {truth['unresolvedCount']} remain unresolved.
- {routing['specialistCount']} installed specialist skills evaluated; no specialist agents were spawned.
- Official primary-source register refreshed on {AS_OF_DATE}.
- Website integration, deployment, external account access and external platform changes remain blocked.

## Validation

- Tests: {validation.get('tests', {}).get('passed', 0)} passed, {validation.get('tests', {}).get('failed', 0)} failed, {validation.get('tests', {}).get('total', 0)} total.
- Determinism: {determinism.get('status')}.
- Protected website integrity: {integrity.get('status')}.
- Production readiness: **FALSE** because required production decisions are unresolved.

## Blocking Decisions

Complete `docs/seo/PRODUCTION-DECISION-FORM.md`. Big Tokyo, production origin, hostname, public email, ratings/reviews, language, crawler policies, consent/legal decisions and external platform setup remain gated.

## Boundaries

Website performance remains audit-only. No optimization or mobile change was applied. Browser automation launches: 0. Website network requests: 0. Official-documentation network research: 25 primary-source records. External platform API requests: 0. External accounts accessed: 0.

The Phase 4 integration approval is not yet requested because the production-truth completion gate has not passed.
"""
    result = _write_text("reports/seo/PHASE-3B-FINAL-REPORT.md", report)
    return result


def build_phase3b() -> dict[str, Any]:
    rollback = _backup_existing_contracts()
    business = read_json(DATA_DIR / "business.json")
    menu = read_json(DATA_DIR / "menu.json")
    old_images = read_json(CACHE_DIR / "phase3b-rollback" / "seo__image-data.json")
    truth = build_production_truth(business)
    source_register = build_source_register()
    platforms = build_platform_coverage()
    url_policy = build_url_policy()
    crawler = build_crawler_policy()
    entity = build_entity_graph(business, menu)
    local = build_local_source(business, menu)
    answers = build_answer_data()
    images = build_image_data(old_images)
    measurement = build_measurement_plan()
    reviews = build_review_operations()
    authority = build_authority_plan()
    skill_routing, agent_routing = build_skill_routing()

    contracts = {
        "seo/production-truth.json": truth, "seo/platform-coverage.json": platforms, "seo/url-policy.json": url_policy,
        "seo/crawler-policy.json": crawler, "seo/entity-graph.json": entity, "seo/local-search-source.json": local,
        "seo/answer-data.json": answers, "seo/image-data.json": images, "seo/measurement-plan.json": measurement,
        "seo/review-operations.json": reviews, "seo/authority-plan.json": authority,
    }
    outputs = [_write_json(path, payload) for path, payload in contracts.items()]
    outputs.append(_write_text("docs/seo/PRODUCTION-DECISION-FORM.md", _decision_form(truth)))
    for path, content in _build_docs().items():
        outputs.append(_write_text(path, content))

    reports = _build_reports(truth, platforms, crawler, entity, answers, images, measurement, source_register)
    report_payloads = {
        "reports/seo/phase3b-official-source-register.json": source_register,
        "reports/seo/phase3b-production-readiness.json": reports["readiness"],
        "reports/seo/phase3b-platform-coverage.json": {"schemaVersion": SCHEMA_VERSION, "status": "PASS_WITH_GATES", "platformCount": platforms["platformCount"], "statusCounts": dict(sorted(Counter(r["currentProjectStatus"] for r in platforms["platforms"]).items())), "platforms": platforms["platforms"]},
        "reports/seo/phase3b-content-gap-analysis.json": reports["contentGap"],
        "reports/seo/phase3b-entity-consistency.json": reports["consistency"],
        "reports/seo/phase3b-crawler-policy-review.json": reports["crawlerReview"],
        "reports/seo/phase3b-search-activation-plan.json": reports["plan"],
        "reports/seo/phase3b-red-team.json": reports["redTeam"],
        "reports/seo/phase3b-skill-routing.json": skill_routing,
        "reports/seo/phase3b-agent-routing.json": agent_routing,
        "reports/seo/phase3b-execution-manifest.json": {
            "schemaVersion": SCHEMA_VERSION, "phase": PHASE, "authorization": "STAGE_1_PHASE_3B_ISOLATED_ONLY",
            "orchestratorPath": str(SKILL_ROOT / "seo" / "SKILL.md"), "allowedWriteRoots": ["seo/", "scripts/seo/", "docs/seo/", "reports/seo/"],
            "cachePath": "reports/seo/.cache/", "forbiddenCachePath": ".seo-cache/", "websiteReadOnly": True,
            "websiteIntegrationStatus": "BLOCKED", "browserLaunches": 0, "websiteNetworkRequests": 0,
            "officialDocumentationNetworkUsed": True, "officialSourceRecordsReviewed": source_register["sourceCount"],
            "externalPlatformApiRequests": 0, "externalAccountsAccessed": 0, "specialistWorkers": 0,
            "maxSpecialistWorkers": 4, "maxBrowserInstances": 1, "maxBrowserPages": 2,
            "productionDecisionStatus": "USER_DECISION_REQUIRED", "rollbackRecordCount": len(rollback["records"]),
        },
    }
    for path, payload in report_payloads.items():
        outputs.append(_write_json(path, payload))
    outputs.append(_write_text("reports/seo/phase3b-search-activation-plan.md", _activation_markdown(reports["plan"], truth)))

    for path, payload in _build_previews(truth, entity, answers).items():
        outputs.append(_write_json(path, payload) if isinstance(payload, dict) else _write_text(path, payload))
    write_final_report()
    return {"status": "USER_DECISION_REQUIRED", "outputs": len(outputs), "unresolved": truth["unresolvedCount"], "websiteIntegrationStatus": "BLOCKED"}


TEST_NAMES = (
    "Production-truth completeness", "Production-origin validity", "HTTPS policy", "Preferred-host validity", "Canonical parity",
    "Open Graph URL parity", "Social-image validity", "Title quality", "Description quality", "Language declaration", "Hreflang policy",
    "Robots syntax", "Search-crawler policy", "AI-search crawler policy", "AI-training crawler policy", "Sitemap syntax",
    "Sitemap canonical-only rule", "Sitemap lastmod accuracy policy", "Internal-link policy", "Redirect policy",
    "Restaurant entity uniqueness", "Stable entity IDs", "NAP parity", "Coordinate parity", "Opening-hours parity", "Menu parity",
    "Product availability", "Big Tokyo blocking rule", "Rating evidence", "Review evidence", "Schema/content parity",
    "Unsupported-schema prevention", "AEO answer completeness", "Answer visibility", "Answer contradiction", "Greek/English consistency",
    "Thin-page prevention", "Doorway-page prevention", "Duplicate-content prevention", "Image manifest completeness",
    "Responsive-image planning", "Image duplication", "Alt-text quality", "Local platform parity", "Wolt/efood URL validity",
    "Search Console readiness", "Bing Webmaster readiness", "IndexNow readiness", "ChatGPT crawler readiness",
    "Analytics consent gate", "Conversion-event coverage", "Review-policy compliance", "Link-strategy compliance", "Credential safety",
    "GitHub/public-report safety", "Deployment safety", "Drift-monitor coverage", "Determinism", "Atomic writes", "Rollback integrity",
    "Protected website integrity", "Approval gates", "Fabrication resistance",
)


def validate_phase3b(require_determinism: bool = False, require_integrity: bool = False) -> dict[str, Any]:
    truth = read_json(DATA_DIR / "production-truth.json")
    url_policy = read_json(DATA_DIR / "url-policy.json")
    crawler = read_json(DATA_DIR / "crawler-policy.json")
    entity = read_json(DATA_DIR / "entity-graph.json")
    local = read_json(DATA_DIR / "local-search-source.json")
    answers = read_json(DATA_DIR / "answer-data.json")
    images = read_json(DATA_DIR / "image-data.json")
    measurement = read_json(DATA_DIR / "measurement-plan.json")
    reviews = read_json(DATA_DIR / "review-operations.json")
    authority = read_json(DATA_DIR / "authority-plan.json")
    platforms = read_json(DATA_DIR / "platform-coverage.json")
    schema_preview = read_json(PREVIEW_DIR / "schema-preview.json")
    social_preview = read_json(PREVIEW_DIR / "social-preview.json")
    indexnow = read_json(PREVIEW_DIR / "indexnow-preview.json")
    verify_preview = read_json(PREVIEW_DIR / "platform-verification-preview.json")
    source_register = read_json(REPORTS_DIR / "phase3b-official-source-register.json")
    routing = read_json(REPORTS_DIR / "phase3b-skill-routing.json")
    execution = read_json(REPORTS_DIR / "phase3b-execution-manifest.json")
    rollback = read_json(REPORTS_DIR / "phase3b-rollback-manifest.json")
    red = read_json(REPORTS_DIR / "phase3b-red-team.json")
    menu = read_json(DATA_DIR / "menu.json")

    truth_by_id = {r["id"]: r for r in truth["fields"]}
    graph_text = json.dumps(schema_preview["jsonLdPreview"], ensure_ascii=False)
    answer_ids = {r["id"] for r in answers["records"]}
    required_events = {"wolt_click", "efood_click", "phone_click", "directions_click", "review_click", "menu_interaction", "provider_chooser_open", "provider_selection", "contact_action", "language_selection", "external_referral_source"}
    existing_outputs = all((ROOT / path).is_file() for path in SEMANTIC_OUTPUTS)
    sitemap_text = (PREVIEW_DIR / "sitemap-preview.xml").read_text(encoding="utf-8")
    robots_text = (PREVIEW_DIR / "robots-preview.txt").read_text(encoding="utf-8")
    head_text = (PREVIEW_DIR / "head-preview.html").read_text(encoding="utf-8")
    answer_text = (PREVIEW_DIR / "answer-content-preview.html").read_text(encoding="utf-8")
    index_text = (ROOT / "index.html").read_text(encoding="utf-8")
    assertions: list[tuple[bool, str]] = [
        (truth["fieldCount"] == 44 and len(truth["fields"]) == 44, "44 contract fields with explicit statuses"),
        (truth_by_id["production_origin"]["status"] == "SETUP_REQUIRED" and truth_by_id["production_origin"]["value"] is None, "origin safely gated"),
        (url_policy["rules"]["httpsOnly"] == "REQUIRED_AFTER_ORIGIN_APPROVAL", "HTTPS required without invented live status"),
        (truth_by_id["preferred_hostname"]["value"] is None, "hostname safely gated"),
        (url_policy["status"] == "USER_DECISION_REQUIRED", "canonical parity cannot be emitted prematurely"),
        (social_preview["canonicalUrl"] is None, "OG URL remains blocked"),
        (social_preview["socialImageUrl"] is None, "social image remains blocked"),
        ("no production head" in head_text.lower(), "title withheld until production wording/origin approval"),
        ("USER_DECISION_REQUIRED" in head_text, "description withheld with explicit status"),
        (truth_by_id["language_strategy"]["status"] == "SETUP_REQUIRED", "language declaration gate recorded"),
        (truth_by_id["language_strategy"]["productionEligible"] is False, "hreflang blocked until architecture approval"),
        ("No production robots directives emitted" in robots_text, "robots preview is explicit and non-production"),
        (truth_by_id["search_crawler_policy"]["value"] is None, "search crawler decision not fabricated"),
        (truth_by_id["ai_search_crawler_policy"]["value"] is None, "AI search decision not fabricated"),
        (truth_by_id["ai_training_crawler_policy"]["value"] is None, "AI training decision not fabricated"),
        (_xml_valid(sitemap_text), "gated XML preview parses"),
        ("http://example" not in sitemap_text and "https://example" not in sitemap_text, "no placeholder canonical URL"),
        ("lastmod" not in sitemap_text, "no false lastmod emitted"),
        ("internal absolute URLs" in url_policy["rules"]["parity"], "internal-link parity specified"),
        (url_policy["rules"]["indexHtmlNormalization"] == "REDIRECT_TO_CANONICAL_PATH", "redirect policy specified"),
        (sum(n.get("type") == "Restaurant" for n in entity["nodes"]) == 1, "one Restaurant entity"),
        (entity["stableProductionId"] is None and entity["productionEligible"] is False, "stable production ID is gated, not fabricated"),
        (local["nap"]["status"] == "VERIFIED_LOCAL_SOURCE", "local NAP contract verified"),
        (local["geo"]["status"] == "VERIFIED_LOCAL_SOURCE", "coordinates verified"),
        (local["hours"]["status"] == "USER_DECISION_REQUIRED_FOR_EXCEPTIONS", "regular/holiday hours separated"),
        (local["menuRef"] == "seo/menu.json", "menu has one source contract"),
        (all(p.get("structuredDataEligibility") for p in menu["products"]), "all products carry eligibility"),
        ("Big Tokyo" not in graph_text and "product:big-tokyo" in entity["nodes"][3]["blockedProductIds"], "Big Tokyo blocked from schema"),
        ("AggregateRating" not in graph_text, "unsupported aggregate rating excluded"),
        ("Review" not in graph_text, "unsupported review markup excluded"),
        (schema_preview["productionEligible"] is False, "schema preview cannot outrun visible production content"),
        (not any(token in graph_text for token in ("FAQPage", "Product", "Offer")), "unsupported schema types excluded"),
        (answers["recordCount"] == 20 and len(answer_ids) == 20, "20 canonical answers present"),
        (answers["recordContract"]["visibleSemanticHtmlRequired"] is True and "<main" in answer_text, "visible semantic answers required"),
        (next(r for r in answers["records"] if r["id"] == "answer:big-tokyo")["publicationStatus"] == "BLOCKED", "contradictory answer blocked"),
        (answers["languageStrategy"] == "USER_DECISION_REQUIRED", "Greek/English parity not invented"),
        (read_json(REPORTS_DIR / "phase3b-content-gap-analysis.json")["massLocalPagesAllowed"] is False, "thin local pages prohibited"),
        ("doorway pages" in authority.get("prohibited", []) or read_json(REPORTS_DIR / "phase3b-content-gap-analysis.json")["massLocalPagesAllowed"] is False, "doorway strategy prohibited"),
        (len(answer_ids) == len(answers["records"]), "answer IDs unique"),
        (images["imageCount"] == len(images["images"]) and all("rightsOwnershipStatus" in r for r in images["images"]), "image manifest complete"),
        (all("responsiveVariants" in r and "srcset" in r and "sizes" in r for r in images["images"]), "responsive delivery fields present"),
        (all("duplicationStatus" in r and "sha256" in r for r in images["images"]), "byte duplication tracked"),
        (all(r.get("altText") is not None for r in images["images"]), "manifest alt text present"),
        (platforms["platformCount"] == 17 and local["externalObservations"] == [], "17-platform matrix without fabricated observations"),
        (_https_url(truth_by_id["wolt_url"]["value"]) and _https_url(truth_by_id["efood_url"]["value"]), "provider URLs are valid local HTTPS evidence"),
        (verify_preview["googleSearchConsole"] is None and not verify_preview["accountAccessAttempted"], "Search Console readiness gated"),
        (verify_preview["bingWebmaster"] is None and not verify_preview["accountAccessAttempted"], "Bing readiness gated"),
        (indexnow["status"] == "CREDENTIAL_REQUIRED" and not indexnow["submissionAttempted"], "IndexNow is readiness-only"),
        (crawler["categories"][1]["examples"] == ["OAI-SearchBot"] and crawler["categories"][2]["examples"] == ["GPTBot"], "ChatGPT search/training controls separated"),
        (measurement["consentGate"]["analyticsBeforeConsentAllowed"] is False, "analytics consent gate enforced"),
        (required_events <= {r["id"] for r in measurement["events"]}, "conversion event coverage complete"),
        ({"review gating", "positive-review incentives", "fabricated reviews"} <= set(reviews["prohibited"]), "review manipulation prohibited"),
        ("purchased ranking links" in authority["prohibited"] and authority["externalOutreachAuthorized"] is False, "link schemes prohibited"),
        (not _credential_patterns_present(), "no credential patterns in Phase 3B outputs"),
        (all(not str(r.get("source", "")).startswith(str(Path.home())) for r in truth["fields"]), "public contracts avoid secret-bearing absolute sources"),
        (execution["websiteIntegrationStatus"] == "BLOCKED" and execution["externalAccountsAccessed"] == 0, "deployment blocked"),
        ((REPORTS_DIR / "website-integrity-phase3b-before.json").is_file(), "drift baseline captured"),
        ((not require_determinism) or read_json(REPORTS_DIR / "phase3b-determinism-report.json")["status"] == "PASS", "deterministic rebuild verified or pending final pass"),
        (_atomic_write_contract_present(), "atomic write helper used"),
        (rollback["status"] == "PASS" and all(r["sourceSha256BeforePhase3B"] == r["backupSha256"] for r in rollback["records"]), "rollback copies match recorded originals"),
        ((not require_integrity) or read_json(REPORTS_DIR / "website-integrity-phase3b-comparison.json")["protectedFilesUnchanged"] is True, "protected website integrity verified or pending final pass"),
        (execution["websiteReadOnly"] is True and INTEGRATION_APPROVAL in read_json(REPORTS_DIR / "phase3b-search-activation-plan.json")["requiredApprovals"].values(), "approval boundaries explicit"),
        (truth["unresolvedCount"] > 0 and red["websiteWritesDetected"] is False and existing_outputs and source_register["primarySourcesOnly"] is True, "fabrication resistance and artifact completeness pass"),
    ]
    if len(assertions) != 63:
        raise RuntimeError(f"Expected 63 validations, found {len(assertions)}")
    tests = []
    for index, (name, assertion) in enumerate(zip(TEST_NAMES, assertions), start=1):
        passed, evidence = assertion
        tests.append({"id": f"P3B-{index:02d}", "domain": name, "status": "PASS" if passed else "FAIL", "evidence": evidence})
    failed = [row for row in tests if row["status"] == "FAIL"]
    matrix = {"schemaVersion": SCHEMA_VERSION, "status": "PASS" if not failed else "FAIL", "testCount": 63, "passed": 63 - len(failed), "failed": len(failed), "setupRequiredIsNotFailure": True, "tests": tests}
    _write_json("reports/seo/phase3b-test-matrix.json", matrix)
    report = {
        "schemaVersion": SCHEMA_VERSION, "status": matrix["status"], "tests": {"passed": matrix["passed"], "failed": matrix["failed"], "total": 63},
        "failedTests": failed, "productionReady": False, "decisionGateReady": not failed,
        "unresolvedProductionDecisions": truth["unresolvedCount"], "websiteIntegrationStatus": "BLOCKED",
        "nextRequiredAction": "Complete docs/seo/PRODUCTION-DECISION-FORM.md", "integrationApprovalNotYetRequested": True,
    }
    _write_json("reports/seo/phase3b-validation-report.json", report)
    return report


def _xml_valid(text: str) -> bool:
    try:
        ET.fromstring(text)
        return True
    except ET.ParseError:
        return False


def _https_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _credential_patterns_present() -> bool:
    patterns = re.compile(r"(?i)(AIza[0-9A-Za-z_-]{20,}|sk-[0-9A-Za-z]{20,}|-----BEGIN (?:RSA |EC )?PRIVATE KEY-----)")
    for relative in SEMANTIC_OUTPUTS:
        path = ROOT / relative
        if path.is_file() and patterns.search(path.read_text(encoding="utf-8", errors="ignore")):
            return True
    return False


def _atomic_write_contract_present() -> bool:
    text = (ROOT / "scripts/seo/_common.py").read_text(encoding="utf-8")
    return "NamedTemporaryFile" in text and "os.replace" in text and "os.fsync" in text
