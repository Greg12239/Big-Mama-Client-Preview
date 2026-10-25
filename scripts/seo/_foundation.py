from __future__ import annotations

import argparse
import html
import json
import re
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from _common import (
    DATA_CONTRACT_VERSION,
    DATA_DIR,
    GENERATOR_VERSION,
    PREVIEW_DIR,
    REPORTS_DIR,
    ROOT,
    FoundationError,
    atomic_write_json,
    atomic_write_text,
    field_value,
    print_result,
    read_json,
    sha256_file,
    utc_now,
)

DATA_FILES = (
    "business.json", "production-decisions.json", "locations.json", "menu.json", "entities.json", "answer-data.json",
    "query-universe.json", "keyword-clusters.json", "intent-map.json",
    "competitor-baseline.json", "local-pack-baseline.json", "citations.json",
    "backlinks.json", "review-operations.json", "content-map.json", "image-data.json",
    "schema-policy.json", "crawler-policy.json", "measurement-plan.json", "data-provenance.json",
)
FORBIDDEN_SCHEMA_TYPES = {"AggregateRating", "Review", "Offer", "Product", "FAQPage", "HowTo"}
QUERY_REQUIRED_FIELDS = {
    "id", "normalizedQuery", "originalQuery", "language", "categories", "intent",
    "geographicModifier", "productModifier", "funnelStage", "targetSearchSurface",
    "evidenceStatus", "source", "observedDate", "targetEntity", "futureTargetUrl",
    "conversionAction", "confidence", "setupRequirements",
}
QUERY_METRIC_FIELDS = {
    "searchVolume", "keywordDifficulty", "cpc", "rank", "localPackPosition",
    "clickEstimates", "trafficPotential",
}
EXPECTED_QUERY_CATEGORIES = {
    "branded", "local-commercial", "maps-near-me", "delivery", "product", "category",
    "comparison", "navigation", "review", "opening-hours", "informational", "greek", "english",
}
FORBIDDEN_PRODUCTION_URL_TOKENS = ("example.com", ".example", "localhost", "127.0.0.1", "file://")


def _load_business() -> dict[str, Any]:
    return read_json(DATA_DIR / "business.json")


def _opening_hours_specifications(business: dict[str, Any]) -> list[dict[str, Any]]:
    hours = field_value(business, "openingHours") or []
    return [
        {"@type": "OpeningHoursSpecification", "dayOfWeek": row["days"], "opens": row["opens"], "closes": row["closes"]}
        for row in hours
    ]


def extract_site_data() -> int:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise FoundationError("BeautifulSoup is required from the verified SEO runtime") from exc

    source = ROOT / "index.html"
    soup = BeautifulSoup(source.read_text(encoding="utf-8"), "html.parser")
    menu_categories: list[dict[str, Any]] = []
    for tab in soup.select("[data-menu-tab]"):
        category_id = tab.get("data-menu-tab")
        panel = soup.select_one(f'[data-menu-panel="{category_id}"]')
        products: list[dict[str, Any]] = []
        for card in panel.select("article.menu-card") if panel else []:
            heading = card.find("h3")
            description = heading.find_next_sibling("p") if heading else None
            badge = card.select_one(".burger-card__badge")
            cta = card.select_one("[data-order-toggle]")
            products.append({
                "name": heading.get_text(" ", strip=True) if heading else None,
                "description": description.get_text(" ", strip=True) if description else None,
                "badge": badge.get_text(" ", strip=True) if badge else None,
                "orderCta": cta.get_text(" ", strip=True) if cta else None,
                "images": [image.get("src") for image in card.select("img[src]")],
                "providers": sorted({link.get("href") for link in card.select("a[data-order-provider]") if link.get("href")}),
            })
        menu_categories.append({"id": category_id, "name": tab.get_text(" ", strip=True), "products": products})

    images = []
    for image in soup.select("img[src]"):
        source_path = image.get("src")
        file_path = ROOT / source_path
        images.append({
            "path": source_path,
            "alt": image.get("alt"),
            "width": int(image["width"]) if image.get("width", "").isdigit() else None,
            "height": int(image["height"]) if image.get("height", "").isdigit() else None,
            "loading": image.get("loading"),
            "exists": file_path.is_file(),
            "size": file_path.stat().st_size if file_path.is_file() else None,
        })

    payload = {
        "schemaVersion": DATA_CONTRACT_VERSION,
        "source": {"path": "index.html", "sha256": sha256_file(source)},
        "metadata": {
            "language": soup.html.get("lang") if soup.html else None,
            "title": soup.title.get_text(strip=True) if soup.title else None,
            "description": soup.select_one('meta[name="description"]').get("content") if soup.select_one('meta[name="description"]') else None,
            "canonical": soup.select_one('link[rel="canonical"]').get("href") if soup.select_one('link[rel="canonical"]') else None,
            "openGraphCount": len(soup.select('meta[property^="og:"]')),
            "twitterCount": len(soup.select('meta[name^="twitter:"]')),
            "schemaBlockCount": len(soup.select('script[type="application/ld+json"]')),
        },
        "menu": menu_categories,
        "images": images,
        "links": sorted({link.get("href") for link in soup.select("a[href]") if link.get("href")}),
        "placeholderOccurrences": soup.get_text(" ", strip=True).casefold().count("placeholder"),
    }
    result = atomic_write_json(REPORTS_DIR / "extracted-site-data.json", payload)
    print_result(result)
    return 0


def build_metadata_preview() -> int:
    business = _load_business()
    decisions = read_json(DATA_DIR / "production-decisions.json")
    origin = field_value(business, "productionOrigin")
    social_image = decisions["decisions"]["socialImage"]["absoluteUrl"]
    title = "Burgers in Nea Filadelfia | Big Mama Burgers n' Fries"
    description = "Explore Big Mama burgers, chicken burgers, hand-cut fries and ordering options in Nea Filadelfia, with location details and posted opening hours."
    canonical = f"{origin.rstrip('/')}/" if origin else None
    lines = [
        "<!doctype html>",
        '<html lang="en">',
        "<head>",
        "  <!-- PREVIEW ONLY: not connected to the website. -->",
        f"  <title>{html.escape(title)}</title>",
        f'  <meta name="description" content="{html.escape(description, quote=True)}">',
        f'  <meta property="og:title" content="{html.escape(title, quote=True)}">',
        f'  <meta property="og:description" content="{html.escape(description, quote=True)}">',
        '  <meta property="og:type" content="website">',
    ]
    if canonical:
        lines.extend([f'  <link rel="canonical" href="{html.escape(canonical, quote=True)}">', f'  <meta property="og:url" content="{html.escape(canonical, quote=True)}">'])
    else:
        lines.append("  <!-- TODO: canonical and og:url omitted until the production origin is VERIFIED. -->")
    if social_image:
        lines.append(f'  <meta property="og:image" content="{html.escape(social_image, quote=True)}">')
    else:
        lines.append("  <!-- TODO: og:image omitted until an absolute social-image URL is VERIFIED. -->")
    lines.extend(["</head>", "</html>"])
    outputs = [atomic_write_text(PREVIEW_DIR / "metadata-preview.html", "\n".join(lines))]
    outputs.append(atomic_write_json(PREVIEW_DIR / "hreflang-preview.json", {
        "status": "NOT_APPLICABLE",
        "currentLanguage": "en",
        "annotations": [],
        "reason": "No approved alternate-language URL exists.",
    }))
    outputs.append(atomic_write_json(PREVIEW_DIR / "manifest-preview.json", {
        "previewOnly": True,
        "name": "Big Mama Burgers n' Fries",
        "short_name": "Big Mama",
        "start_url": "/",
        "display": "standalone",
        "icons": [],
        "status": "SETUP_REQUIRED",
        "limitations": ["No favicon or approved manifest icons are verified."],
    }))
    print_result({"outputs": outputs, "productionOrigin": "VERIFIED" if origin else "SETUP_REQUIRED", "socialImage": "VERIFIED" if social_image else "SETUP_REQUIRED"})
    return 0


def _schema_preview_payload() -> dict[str, Any]:
    business = _load_business()
    menu = read_json(DATA_DIR / "menu.json")
    decisions = read_json(DATA_DIR / "production-decisions.json")
    origin = field_value(business, "productionOrigin")
    social_image = decisions["decisions"]["socialImage"]["absoluteUrl"]
    address = field_value(business, "address")
    geo = field_value(business, "geo")
    restaurant: dict[str, Any] = {
        "@type": "Restaurant",
        "name": field_value(business, "canonicalBrandName"),
        "address": {"@type": "PostalAddress", **address},
        "geo": {"@type": "GeoCoordinates", **geo},
        "telephone": field_value(business, "telephone"),
        "openingHoursSpecification": _opening_hours_specifications(business),
    }
    sections = []
    for category in sorted(menu["categories"], key=lambda row: row["position"]):
        items = []
        for product in sorted((row for row in menu["products"] if row["categoryId"] == category["id"]), key=lambda row: row["position"]):
            if product["structuredDataEligibility"] == "BLOCKED_CONTRADICTION":
                continue
            items.append({"@type": "MenuItem", "name": product["name"], "description": product["description"]})
        sections.append({"@type": "MenuSection", "name": category["name"], "hasMenuItem": items})
    restaurant["hasMenu"] = {"@type": "Menu", "name": "Big Mama Menu", "hasMenuSection": sections}
    graph: list[dict[str, Any]] = []
    omitted_entities: list[dict[str, str]] = []
    if origin:
        canonical = f"{origin.rstrip('/')}/"
        restaurant["@id"] = f"{canonical}#restaurant"
        restaurant["url"] = canonical
        website = {"@type": "WebSite", "@id": f"{canonical}#website", "url": canonical, "name": field_value(business, "canonicalBrandName")}
        webpage = {"@type": "WebPage", "@id": f"{canonical}#webpage", "url": canonical, "name": "Big Mama Burgers n' Fries", "isPartOf": {"@id": website["@id"]}, "about": {"@id": restaurant["@id"]}}
        graph.extend([website, webpage])
    else:
        omitted_entities.extend([
            {"type": "WebSite", "reason": "Production origin is SETUP_REQUIRED."},
            {"type": "WebPage", "reason": "Production origin is SETUP_REQUIRED."},
        ])
    if origin and social_image:
        image_object = {"@type": "ImageObject", "@id": f"{origin.rstrip('/')}/#social-image", "contentUrl": social_image}
        graph.append(image_object)
    else:
        omitted_entities.append({"type": "ImageObject", "reason": "Approved absolute social-image URL is SETUP_REQUIRED."})
    omitted_entities.append({"type": "Place", "reason": "Restaurant already represents the same physical place; duplicate node omitted."})
    graph.append(restaurant)
    return {
        "previewStatus": "PREVIEW_READY" if origin and social_image else "PASS_WITH_SETUP_REQUIRED",
        "productionEligible": False,
        "integrationStatus": "PROHIBITED",
        "limitations": [item for item in [
            None if origin else "Production origin is not verified; canonical URLs and public @id values are omitted.",
            None if social_image else "Approved absolute social-image URL is unavailable; ImageObject is omitted.",
            "Website integration is not authorized.",
        ] if item],
        "omittedEntities": omitted_entities,
        "excludedEntities": [{"id": "product:big-tokyo", "reason": "Visible COMING SOON and Order now contradiction."}],
        "jsonLd": {"@context": "https://schema.org", "@graph": graph},
    }


def build_schema_preview() -> int:
    result = atomic_write_json(PREVIEW_DIR / "schema-preview.json", _schema_preview_payload())
    print_result(result)
    return 0


def build_sitemap_preview() -> int:
    origin = field_value(_load_business(), "productionOrigin")
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    root = ET.Element("{http://www.sitemaps.org/schemas/sitemap/0.9}urlset")
    if origin:
        node = ET.SubElement(root, "{http://www.sitemaps.org/schemas/sitemap/0.9}url")
        ET.SubElement(node, "{http://www.sitemaps.org/schemas/sitemap/0.9}loc").text = f"{origin.rstrip('/')}/"
    xml_body = ET.tostring(root, encoding="unicode", short_empty_elements=True)
    note = "" if origin else "<!-- SETUP_REQUIRED: production origin is not verified; no URL is emitted. -->\n"
    result = atomic_write_text(PREVIEW_DIR / "sitemap-preview.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n{note}{xml_body}')
    print_result({**result, "status": "PREVIEW_READY" if origin else "SETUP_REQUIRED"})
    return 0


def build_robots_preview() -> int:
    business = _load_business()
    origin = field_value(business, "productionOrigin")
    lines = ["# PREVIEW ONLY - NOT FOR DEPLOYMENT", "User-agent: *", "Allow: /"]
    if origin:
        lines.append(f"Sitemap: {origin.rstrip('/')}/sitemap.xml")
    else:
        lines.append("# Sitemap omitted: production origin is SETUP_REQUIRED")
    lines.append("# AI crawler and training policies require separate human approval.")
    result = atomic_write_text(PREVIEW_DIR / "robots-preview.txt", "\n".join(lines))
    print_result(result)
    return 0


def build_answer_preview() -> int:
    records = read_json(DATA_DIR / "answer-data.json")["records"]
    eligible = [row for row in records if row.get("answer") and row.get("verificationStatus") in {"VERIFIED", "OBSERVED"}]
    result = atomic_write_json(PREVIEW_DIR / "answer-preview.json", {
        "previewOnly": True,
        "schemaMarkupGenerated": False,
        "hiddenContentGenerated": False,
        "websiteIntegrationStatus": "PROHIBITED",
        "records": eligible,
        "blockedRecordIds": sorted(row["id"] for row in records if not row.get("answer")),
    })
    print_result(result)
    return 0


def _is_safe_absolute_url(value: str) -> bool:
    parsed = urlparse(value)
    lowered = value.casefold()
    return (
        parsed.scheme == "https"
        and bool(parsed.netloc)
        and not parsed.fragment
        and not any(token in lowered for token in FORBIDDEN_PRODUCTION_URL_TOKENS)
    )


def validate_search_data(production_ready: bool = False) -> int:
    errors: list[str] = []
    warnings: list[str] = []
    setup_required: list[str] = []
    checks: dict[str, Any] = {}
    for filename in DATA_FILES:
        path = DATA_DIR / filename
        if not path.is_file():
            errors.append(f"Missing required data contract: seo/{filename}")
            continue
        try:
            payload = read_json(path)
        except (OSError, json.JSONDecodeError) as exc:
            errors.append(f"Invalid JSON in seo/{filename}: {exc}")
            continue
        if payload.get("schemaVersion") != DATA_CONTRACT_VERSION:
            errors.append(f"Unsupported schemaVersion in seo/{filename}")

    business = _load_business()
    decisions = read_json(DATA_DIR / "production-decisions.json")
    for name in ("canonicalBrandName", "address", "telephone", "geo", "openingHours", "orderingUrls"):
        field = business["fields"].get(name, {})
        if field.get("value") in (None, "", []) or field.get("verificationStatus") != "VERIFIED":
            errors.append(f"Required verified business field is unavailable: {name}")

    origin = field_value(business, "productionOrigin")
    decision_origin = decisions["decisions"]["productionOrigin"]["value"]
    social_image = decisions["decisions"]["socialImage"]["absoluteUrl"]
    if origin != decision_origin:
        errors.append("Production-origin decision does not match seo/business.json.")
    if origin is None:
        setup_required.append("Verified production origin is required for canonical, sitemap, and public @id output.")
    elif not _is_safe_absolute_url(origin):
        errors.append("Production origin must be a verified absolute HTTPS origin without placeholders, fragments, localhost, or file URLs.")
    if social_image is None:
        setup_required.append("Approved absolute social image URL is unavailable.")
    elif not _is_safe_absolute_url(social_image):
        errors.append("Social-image URL must be a verified absolute HTTPS URL without placeholders, fragments, localhost, or file URLs.")
    if business["fields"]["socialImageUrl"]["value"] != social_image:
        errors.append("Social-image decision does not match seo/business.json.")
    if business["fields"]["publicEmail"]["value"] is not None:
        errors.append("Public email must remain null until independently verified.")
    if business["fields"]["socialProfiles"]["value"]:
        errors.append("Social profiles must remain empty until independently verified.")
    protected_html = (ROOT / "index.html").read_text(encoding="utf-8")
    if re.search(r"mailto:[^\"']+\.example(?:[\"'])", protected_html, re.IGNORECASE):
        warnings.append("The protected website contains an observed placeholder email; it remains excluded from production-eligible search data.")
    checks["productionDecisionConsistency"] = not any("decision does not match" in item for item in errors)

    query_universe = read_json(DATA_DIR / "query-universe.json")
    query_ids: list[str] = []
    observed_categories: set[str] = set()
    query_contract_errors = 0
    for row in query_universe.get("queries", []):
        query_ids.append(row.get("id"))
        missing = sorted(QUERY_REQUIRED_FIELDS - set(row))
        if missing:
            errors.append(f"Query {row.get('id', '[missing id]')} is missing fields: {', '.join(missing)}")
            query_contract_errors += 1
        metrics_present = QUERY_METRIC_FIELDS & set(row)
        if metrics_present != QUERY_METRIC_FIELDS or any(row.get(name) is not None for name in QUERY_METRIC_FIELDS):
            errors.append(f"Query {row.get('id', '[missing id]')} must expose all live metrics as null.")
            query_contract_errors += 1
        normalized = row.get("normalizedQuery")
        if not isinstance(normalized, str) or normalized != normalized.strip().lower():
            errors.append(f"Query {row.get('id', '[missing id]')} has a non-normalized normalizedQuery.")
            query_contract_errors += 1
        observed_categories.update(row.get("categories", []))
        future_url = row.get("futureTargetUrl")
        if future_url is not None and not _is_safe_absolute_url(future_url):
            errors.append(f"Query {row.get('id', '[missing id]')} has an unsafe futureTargetUrl.")
            query_contract_errors += 1
    if len(query_ids) != len(set(query_ids)):
        errors.append("Duplicate query IDs detected.")
        query_contract_errors += 1
    missing_categories = sorted(EXPECTED_QUERY_CATEGORIES - observed_categories)
    if missing_categories:
        errors.append(f"Query category coverage is incomplete: {', '.join(missing_categories)}")
        query_contract_errors += 1
    checks["queryContract"] = {"passed": query_contract_errors == 0, "queryCount": len(query_ids), "categoryCount": len(observed_categories)}

    clusters = read_json(DATA_DIR / "keyword-clusters.json")["clusters"]
    clustered_ids = [query_id for cluster in clusters for query_id in cluster["queryIds"]]
    unknown_cluster_ids = sorted(set(clustered_ids) - set(query_ids))
    unclustered_ids = sorted(set(query_ids) - set(clustered_ids))
    duplicate_cluster_ids = sorted(query_id for query_id, count in Counter(clustered_ids).items() if count > 1)
    if unknown_cluster_ids:
        errors.append(f"Clusters reference unknown query IDs: {', '.join(unknown_cluster_ids)}")
    if unclustered_ids:
        errors.append(f"Queries are missing from clusters: {', '.join(unclustered_ids)}")
    if duplicate_cluster_ids:
        errors.append(f"Queries appear in multiple clusters: {', '.join(duplicate_cluster_ids)}")
    checks["clusterReferences"] = not (unknown_cluster_ids or unclustered_ids or duplicate_cluster_ids)

    competitor = read_json(DATA_DIR / "competitor-baseline.json")
    competitor_required = set(competitor["observationContract"]["requiredFields"])
    for observation in competitor["observations"]:
        missing = sorted(competitor_required - set(observation))
        if missing:
            errors.append(f"Competitor observation is missing fields: {', '.join(missing)}")
    checks["competitorObservationCount"] = len(competitor["observations"])

    local_pack = read_json(DATA_DIR / "local-pack-baseline.json")
    local_required = set(local_pack["observationContract"]["requiredFields"])
    for observation in local_pack["observations"]:
        missing = sorted(local_required - set(observation))
        if missing:
            errors.append(f"Local Pack observation is missing fields: {', '.join(missing)}")
    checks["localPackObservationCount"] = len(local_pack["observations"])

    answers = read_json(DATA_DIR / "answer-data.json")
    answer_required = set(answers["recordContract"]["requiredFields"])
    for row in answers["records"]:
        missing = sorted(answer_required - set(row))
        if missing:
            errors.append(f"Answer {row.get('id', '[missing id]')} is missing fields: {', '.join(missing)}")
        if str(row.get("futureVisiblePlacement", "")).casefold() == "hidden":
            errors.append(f"Answer {row.get('id')} recommends hidden AEO content.")
        if row.get("publicationStatus") not in {"PREVIEW_ONLY", "BLOCKED"}:
            errors.append(f"Answer {row.get('id')} has an unauthorized publication status.")
    checks["answerRecordCount"] = len(answers["records"])

    menu = read_json(DATA_DIR / "menu.json")
    big_tokyo = next((product for product in menu["products"] if product["id"] == "product:big-tokyo"), None)
    if big_tokyo is None or big_tokyo.get("structuredDataEligibility") != "BLOCKED_CONTRADICTION" or not big_tokyo.get("contradictions"):
        errors.append("Big Tokyo must remain blocked from structured data by its documented availability contradiction.")
    if any(product.get("availability") is not None for product in menu["products"]):
        errors.append("Menu availability must remain null until verified.")
    prohibited_unknowns = menu.get("prohibitedUnknowns", {})
    if any(value is not None for value in prohibited_unknowns.values()):
        errors.append("Unknown Menu prices, Offers, stock, allergens, and nutrition must remain null.")
    if any(product.get("contradictions") for product in menu["products"]):
        warnings.append("Menu contradictions exist; affected products remain blocked from schema eligibility.")
    checks["bigTokyoBlocked"] = big_tokyo is not None and big_tokyo.get("structuredDataEligibility") == "BLOCKED_CONTRADICTION"

    reviews = read_json(DATA_DIR / "review-operations.json")
    if reviews["observedWebsiteSignals"].get("aggregateRatingSchemaEligible") is not False:
        errors.append("Observed website rating text must remain ineligible for aggregate-rating schema.")
    for field in ("rating", "reviewCount"):
        if reviews["monthlyMetrics"].get(field) is not None:
            errors.append(f"Live review metric must remain null: {field}")

    crawler = read_json(DATA_DIR / "crawler-policy.json")
    if crawler["searchIndexingRecommendation"].get("productionAuthorized") is not False:
        errors.append("Crawler policy cannot be production-authorized in this phase.")
    crawler_values = list(crawler["aiSearchAccess"]["crawlers"].values()) + list(crawler["aiTrainingAccess"]["crawlers"].values())
    if any(value != "UNDECIDED" for value in crawler_values):
        errors.append("AI crawler decisions must remain UNDECIDED until human approval.")
    warnings.append("Crawler, AI-search, and AI-training policies remain human decisions and are not production authorized.")
    checks["crawlerPolicyAuthorized"] = False

    sitemap_path = PREVIEW_DIR / "sitemap-preview.xml"
    if sitemap_path.is_file():
        try:
            sitemap_root = ET.parse(sitemap_path).getroot()
            sitemap_locs = [node.text for node in sitemap_root.findall("{http://www.sitemaps.org/schemas/sitemap/0.9}url/{http://www.sitemaps.org/schemas/sitemap/0.9}loc") if node.text]
        except ET.ParseError as exc:
            errors.append(f"Malformed sitemap preview: {exc}")
            sitemap_locs = []
        if any(urlparse(value).fragment for value in sitemap_locs):
            errors.append("Sitemap preview contains a fragment URL.")
        if origin is None and sitemap_locs:
            errors.append("Sitemap preview must contain no URLs while production origin is unresolved.")
        if origin and any(not value.startswith(f"{origin.rstrip('/')}/") for value in sitemap_locs):
            errors.append("Sitemap preview URL does not match the production origin.")
    else:
        errors.append("Sitemap preview is missing.")

    robots_path = PREVIEW_DIR / "robots-preview.txt"
    if robots_path.is_file():
        sitemap_directives = [line.split(":", 1)[1].strip() for line in robots_path.read_text(encoding="utf-8").splitlines() if line.casefold().startswith("sitemap:")]
        if origin is None and sitemap_directives:
            errors.append("Robots preview must omit Sitemap while production origin is unresolved.")
        if origin and sitemap_directives != [f"{origin.rstrip('/')}/sitemap.xml"]:
            errors.append("Robots preview sitemap directive does not match the production origin.")
    else:
        errors.append("Robots preview is missing.")
    checks["sitemapUrlCount"] = len(sitemap_locs) if sitemap_path.is_file() else 0

    phase2_integrity_path = REPORTS_DIR / "website-integrity-phase2-comparison.json"
    integrity_path = phase2_integrity_path if phase2_integrity_path.is_file() else REPORTS_DIR / "website-integrity-comparison.json"
    if integrity_path.is_file() and read_json(integrity_path).get("status") == "FAIL":
        errors.append("Latest protected website integrity comparison reports FAIL.")
    checks["latestIntegrityStatus"] = read_json(integrity_path).get("status") if integrity_path.is_file() else "MISSING"

    if (ROOT / ".seo-cache").exists():
        errors.append("Prohibited root .seo-cache exists.")
    checks["cacheRoot"] = "reports/seo/.cache"
    checks["forbiddenRootCacheAbsent"] = not (ROOT / ".seo-cache").exists()

    status = "FAIL" if errors else ("PASS_WITH_SETUP_REQUIRED" if setup_required else "PASS")
    report = {
        "schemaVersion": DATA_CONTRACT_VERSION,
        "generatedAt": utc_now(),
        "status": status,
        "productionReady": not errors and not setup_required and decisions.get("deploymentReady") is True,
        "errors": errors,
        "warnings": warnings,
        "setupRequired": setup_required,
        "checks": checks,
        "filesValidated": len(DATA_FILES),
        "networkRequests": 0,
        "browserLaunches": 0,
        "websiteWrites": 0,
    }
    write_result = atomic_write_json(REPORTS_DIR / "seo-validation-report.json", report)
    print_result({"report": write_result, **report})
    if errors or (production_ready and setup_required):
        return 2
    return 0


def _walk_schema_types(value: Any) -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        schema_type = value.get("@type")
        if isinstance(schema_type, str):
            found.append(schema_type)
        elif isinstance(schema_type, list):
            found.extend(str(item) for item in schema_type)
        for child in value.values():
            found.extend(_walk_schema_types(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk_schema_types(child))
    return found


def _walk_schema_urls(value: Any) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"@id", "url", "contentUrl"} and isinstance(child, str):
                found.append((key, child))
            found.extend(_walk_schema_urls(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_walk_schema_urls(child))
    return found


def validate_schema_preview() -> int:
    path = PREVIEW_DIR / "schema-preview.json"
    payload = read_json(path)
    errors: list[str] = []
    json_ld = payload.get("jsonLd")
    if not isinstance(json_ld, dict) or json_ld.get("@context") != "https://schema.org":
        errors.append("JSON-LD context is missing or invalid.")
    detected = sorted(set(_walk_schema_types(json_ld)))
    prohibited = sorted(set(detected) & FORBIDDEN_SCHEMA_TYPES)
    if prohibited:
        errors.append(f"Prohibited schema types detected: {', '.join(prohibited)}")
    allowed = set(read_json(DATA_DIR / "schema-policy.json")["allowedTypes"])
    unsupported = sorted(set(detected) - allowed - {"OpeningHoursSpecification"})
    if unsupported:
        errors.append(f"Unsupported schema types detected: {', '.join(unsupported)}")
    serialized = json.dumps(json_ld, ensure_ascii=False)
    if re.search(r"\[[A-Za-z][^\]]+\]", serialized):
        errors.append("Placeholder values detected in schema preview.")
    url_values = _walk_schema_urls(json_ld)
    for key, value in url_values:
        if not _is_safe_absolute_url(value):
            errors.append(f"Schema {key} is not a safe absolute HTTPS URL: {value}")
    origin = field_value(_load_business(), "productionOrigin")
    if origin is None and url_values:
        errors.append("Schema preview must omit public URL and @id values while production origin is unresolved.")
    if "Big Tokyo" in serialized:
        errors.append("Big Tokyo must remain excluded from schema preview.")
    report = {
        "generatedAt": utc_now(),
        "status": "PASS" if not errors else "FAIL",
        "detectedTypes": detected,
        "schemaUrlCount": len(url_values),
        "bigTokyoExcluded": "Big Tokyo" not in serialized,
        "prohibitedTypesExcluded": not prohibited,
        "errors": errors,
        "previewStatus": payload.get("previewStatus"),
        "productionEligible": payload.get("productionEligible"),
    }
    result = atomic_write_json(REPORTS_DIR / "schema-validation-report.json", report)
    print_result({"report": result, **report})
    return 0 if not errors else 2


def validate_nap() -> int:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise FoundationError("BeautifulSoup is required from the verified SEO runtime") from exc
    business = _load_business()
    location = read_json(DATA_DIR / "locations.json")["locations"][0]
    soup = BeautifulSoup((ROOT / "index.html").read_text(encoding="utf-8"), "html.parser")
    visible_text = " ".join(soup.stripped_strings)
    expected_name = field_value(business, "canonicalBrandName")
    expected_address = field_value(business, "address")
    expected_phone = field_value(business, "telephone")
    checks = {
        "businessLocationNameMatch": location["name"] == expected_name,
        "businessLocationPhoneMatch": location["telephone"] == expected_phone,
        "businessLocationAddressMatch": location["address"] == expected_address,
        "visiblePhoneObserved": expected_phone in visible_text,
        "visibleStreetObserved": expected_address["streetAddress"] in visible_text,
        "visibleLocalityObserved": expected_address["addressLocality"] in visible_text,
    }
    mismatches = sorted(name for name, passed in checks.items() if not passed)
    report = {"generatedAt": utc_now(), "status": "PASS" if not mismatches else "FAIL", "checks": checks, "mismatches": mismatches, "sources": ["seo/business.json", "seo/locations.json", "index.html"]}
    result = atomic_write_json(REPORTS_DIR / "nap-consistency-report.json", report)
    print_result({"report": result, **report})
    return 0 if not mismatches else 2


def validate_menu_consistency() -> int:
    menu = read_json(DATA_DIR / "menu.json")
    category_ids = {row["id"] for row in menu["categories"]}
    product_ids = [row["id"] for row in menu["products"]]
    errors: list[str] = []
    warnings: list[dict[str, Any]] = []
    if len(product_ids) != len(set(product_ids)):
        errors.append("Duplicate product IDs detected.")
    for product in menu["products"]:
        if product["categoryId"] not in category_ids:
            errors.append(f"Unknown category for {product['id']}")
        if product.get("visibleBadge", "").casefold() == "coming soon" and product.get("orderState") == "ORDER_NOW_VISIBLE":
            warnings.append({"productId": product["id"], "issue": "COMING_SOON_WITH_ORDER_NOW", "schemaEligibility": product["structuredDataEligibility"]})
            if product.get("structuredDataEligibility") != "BLOCKED_CONTRADICTION":
                errors.append(f"Contradictory product must be blocked from schema: {product['id']}")
        if product.get("availability") is not None:
            errors.append(f"Unverified availability must remain null: {product['id']}")
    if any(value is not None for value in menu.get("prohibitedUnknowns", {}).values()):
        errors.append("Menu prohibited unknowns must remain null.")
    report = {"generatedAt": utc_now(), "status": "PASS_WITH_WARNINGS" if warnings and not errors else ("PASS" if not errors else "FAIL"), "categoryCount": len(category_ids), "productCount": len(product_ids), "errors": errors, "contradictions": warnings}
    result = atomic_write_json(REPORTS_DIR / "menu-consistency-report.json", report)
    print_result({"report": result, **report})
    return 0 if not errors else 2


def validate_assets() -> int:
    inventory = read_json(DATA_DIR / "image-data.json")["images"]
    errors: list[str] = []
    warnings: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in inventory:
        source = row["sourcePath"]
        if source in seen:
            errors.append(f"Duplicate image sourcePath: {source}")
        seen.add(source)
        path = (ROOT / source).resolve()
        if not path.is_file() or not path.is_relative_to((ROOT / "public").resolve()):
            errors.append(f"Missing or unsafe image path: {source}")
            continue
        actual_size = path.stat().st_size
        if actual_size != row["fileSize"]:
            errors.append(f"File size mismatch for {source}: expected {row['fileSize']}, got {actual_size}")
        if actual_size > 700_000:
            warnings.append({"path": source, "bytes": actual_size, "classification": "STATIC_CODE_FINDING", "action": "recommendation-only"})
    report = {"generatedAt": utc_now(), "status": "PASS_WITH_WARNINGS" if warnings and not errors else ("PASS" if not errors else "FAIL"), "assetsChecked": len(inventory), "errors": errors, "oversizedObservations": warnings, "assetsModified": False}
    result = atomic_write_json(REPORTS_DIR / "asset-validation-report.json", report)
    print_result({"report": result, **report})
    return 0 if not errors else 2


def validate_internal_links() -> int:
    try:
        from bs4 import BeautifulSoup
    except ImportError as exc:
        raise FoundationError("BeautifulSoup is required from the verified SEO runtime") from exc
    soup = BeautifulSoup((ROOT / "index.html").read_text(encoding="utf-8"), "html.parser")
    ids = {node.get("id") for node in soup.select("[id]") if node.get("id")}
    links = []
    broken_fragments = []
    placeholders = []
    for anchor in soup.select("a[href]"):
        href = anchor.get("href")
        links.append({"href": href, "label": anchor.get_text(" ", strip=True), "external": href.startswith(("http://", "https://"))})
        if href.startswith("#") and href[1:] not in ids:
            broken_fragments.append(href)
        if href in {"#", "", "javascript:void(0)"}:
            placeholders.append(href)
    report = {"generatedAt": utc_now(), "status": "PASS" if not broken_fragments else "FAIL", "linkCount": len(links), "brokenFragments": sorted(set(broken_fragments)), "placeholderLinks": sorted(set(placeholders)), "links": links}
    result = atomic_write_json(REPORTS_DIR / "internal-link-report.json", report)
    print_result({"report": result, "status": report["status"], "linkCount": len(links)})
    return 0 if not broken_fragments else 2


def detect_placeholders() -> int:
    patterns = ("placeholder", "example.com", "lorem ipsum", "TODO")
    findings = []
    for path in (ROOT / "index.html", ROOT / "styles.css", ROOT / "app.js"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            for pattern in patterns:
                if pattern.casefold() in line.casefold():
                    findings.append({"path": path.relative_to(ROOT).as_posix(), "line": number, "pattern": pattern, "classification": "OBSERVED"})
    report = {"generatedAt": utc_now(), "status": "FINDINGS", "findings": findings, "websiteModified": False}
    result = atomic_write_json(REPORTS_DIR / "placeholder-report.json", report)
    print_result({"report": result, "findingCount": len(findings)})
    return 0


def _discover_protected_files() -> list[Path]:
    fixed = {ROOT / name for name in (".gitignore", ".nojekyll", "AGENTS.md", "README.md", "codex_control_manifest.json", "index.html", "styles.css", "app.js", "robots.txt", "sitemap.xml", "site.webmanifest", "manifest.json", "favicon.ico")}
    fixed.update(path for path in ROOT.iterdir() if path.is_file() and path.suffix.casefold() in {".html", ".css", ".js", ".mjs", ".cjs"})
    public_root = ROOT / "public"
    if public_root.is_dir():
        fixed.update(path for path in public_root.rglob("*") if path.is_file())
    return sorted((path for path in fixed if path.is_file()), key=lambda item: item.relative_to(ROOT).as_posix().casefold())


def build_integrity_manifest(output: Path, label: str) -> int:
    files = _discover_protected_files()
    records = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
            "last_write_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        for path in files
    ]
    payload = {"schema_version": "1.1.0", "manifest_label": label, "baseline_timestamp": utc_now(), "repository_root": ".", "hash_algorithm": "SHA-256", "protected_file_count": len(records), "aggregate_bytes": sum(row["size"] for row in records), "files": records}
    result = atomic_write_json(output, payload)
    print_result({"output": result, "protectedFileCount": len(records)})
    return 0


def compare_integrity(before: Path, after: Path, output: Path) -> int:
    before_payload = read_json(before)
    after_payload = read_json(after)
    before_files = {row["path"]: row for row in before_payload["files"]}
    after_files = {row["path"]: row for row in after_payload["files"]}
    added = sorted(set(after_files) - set(before_files))
    deleted = sorted(set(before_files) - set(after_files))
    changed = sorted(path for path in set(before_files) & set(after_files) if before_files[path]["sha256"] != after_files[path]["sha256"])
    size_changed = sorted(path for path in set(before_files) & set(after_files) if before_files[path]["size"] != after_files[path]["size"])
    added_by_hash: dict[str, list[str]] = {}
    for path in added:
        added_by_hash.setdefault(after_files[path]["sha256"], []).append(path)
    renamed = []
    for old_path in deleted:
        candidates = added_by_hash.get(before_files[old_path]["sha256"], [])
        if candidates:
            renamed.append({"from": old_path, "to": candidates[0]})
    before_bytes = sum(row["size"] for row in before_files.values())
    after_bytes = sum(row["size"] for row in after_files.values())
    report = {
        "generatedAt": utc_now(),
        "status": "PASS" if not (added or deleted or changed) else "FAIL",
        "protectedFilesUnchanged": not (added or deleted or changed),
        "added": added,
        "deleted": deleted,
        "changed": changed,
        "sizeChanged": size_changed,
        "renamed": renamed,
        "beforeCount": len(before_files),
        "afterCount": len(after_files),
        "beforeAggregateBytes": before_bytes,
        "afterAggregateBytes": after_bytes,
        "aggregateBytesUnchanged": before_bytes == after_bytes,
    }
    result = atomic_write_json(output, report)
    print_result({"output": result, **report})
    return 0 if report["status"] == "PASS" else 2


def compare_competitor_baseline() -> int:
    baseline = read_json(DATA_DIR / "competitor-baseline.json")
    report = {"generatedAt": utc_now(), "status": baseline["status"], "baselineCompetitorCount": len(baseline["competitors"]), "observationCount": len(baseline["observations"]), "competitorTypesSupported": baseline["competitorTypes"], "manualCollectionPlanStatus": baseline["collectionPlans"][0]["status"], "apiCollectionPlanStatus": baseline["collectionPlans"][1]["status"], "currentCompetitorCount": 0, "added": [], "removed": [], "changed": [], "networkRequests": 0, "limitations": ["No authorized external competitor observations exist."]}
    result = atomic_write_json(REPORTS_DIR / "competitor-gap-report.json", report)
    print_result({"report": result, **report})
    return 0


def build_local_search_baseline() -> int:
    business = _load_business()
    location = read_json(DATA_DIR / "locations.json")["locations"][0]
    citations = read_json(DATA_DIR / "citations.json")
    local_pack = read_json(DATA_DIR / "local-pack-baseline.json")
    payload = {
        "generatedAt": utc_now(),
        "status": "PASS_WITH_SETUP_REQUIRED",
        "businessType": "brick-and-mortar",
        "industry": "restaurant",
        "location": {
            "id": location["id"],
            "name": location["name"],
            "address": location["address"],
            "telephone": location["telephone"],
            "geo": location["geo"],
            "verificationStatus": location["verificationStatus"],
        },
        "productionOriginStatus": business["fields"]["productionOrigin"]["verificationStatus"],
        "observedCitationCount": len(citations["records"]),
        "localPackObservationCount": len(local_pack["observations"]),
        "geoGridStatus": local_pack["geoGridReadiness"]["status"],
        "gbpChecklist": local_pack["googleBusinessProfileReadiness"],
        "observationContract": local_pack["observationContract"],
        "externalAccounts": {
            "googleBusinessProfile": "NOT_VERIFIED",
            "googleSearchConsole": "NOT_VERIFIED",
            "bingWebmasterTools": "NOT_VERIFIED",
            "analytics": "NOT_VERIFIED",
        },
        "limitations": ["No live Local Pack, Maps, GBP, citation, review, or ranking data was collected."],
        "networkRequests": 0,
        "browserLaunches": 0,
    }
    result = atomic_write_json(REPORTS_DIR / "local-search-baseline.json", payload)
    print_result(result)
    return 0


def compare_search_drift() -> int:
    provenance = read_json(DATA_DIR / "data-provenance.json")
    tracked = {row["path"]: row["sha256"] for row in provenance["sources"] if row.get("path") and row.get("sha256")}
    observations = []
    for relative, expected in sorted(tracked.items()):
        path = ROOT / relative
        actual = sha256_file(path) if path.is_file() else None
        observations.append({"path": relative, "expectedSha256": expected, "actualSha256": actual, "status": "UNCHANGED" if actual == expected else "DRIFT"})
    drift = [row for row in observations if row["status"] == "DRIFT"]
    report = {"generatedAt": utc_now(), "status": "PASS" if not drift else "FAIL", "observations": observations, "drift": drift}
    result = atomic_write_json(REPORTS_DIR / "search-drift-report.json", report)
    print_result({"report": result, "status": report["status"], "driftCount": len(drift)})
    return 0 if not drift else 2


def build_performance_inventory() -> int:
    protected = _discover_protected_files()
    extensions = Counter(path.suffix.casefold() or "[none]" for path in protected)
    public_assets = [path for path in protected if path.is_relative_to(ROOT / "public")]
    largest = sorted(public_assets, key=lambda path: path.stat().st_size, reverse=True)[:10]
    payload = {
        "generatedAt": utc_now(),
        "evidenceClassification": "STATIC_CODE_FINDING",
        "websiteModified": False,
        "protectedFileCount": len(protected),
        "protectedBytes": sum(path.stat().st_size for path in protected),
        "publicAssetCount": len(public_assets),
        "publicAssetBytes": sum(path.stat().st_size for path in public_assets),
        "extensionCounts": dict(sorted(extensions.items())),
        "entryFiles": {name: (ROOT / name).stat().st_size for name in ("index.html", "styles.css", "app.js")},
        "largestAssets": [{"path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size} for path in largest],
        "laboratoryData": "NOT_COLLECTED",
        "fieldData": "FIELD_DATA_UNAVAILABLE",
        "recommendationsOnly": True,
    }
    result = atomic_write_json(REPORTS_DIR / "performance" / "website-performance-inventory.json", payload)
    print_result(result)
    return 0


def generate_search_report() -> int:
    validation = read_json(REPORTS_DIR / "seo-validation-report.json")
    nap = read_json(REPORTS_DIR / "nap-consistency-report.json")
    menu = read_json(REPORTS_DIR / "menu-consistency-report.json")
    phase2_integrity_path = REPORTS_DIR / "website-integrity-phase2-comparison.json"
    integrity_path = phase2_integrity_path if phase2_integrity_path.is_file() else REPORTS_DIR / "website-integrity-comparison.json"
    integrity = read_json(integrity_path) if integrity_path.is_file() else {"status": "PENDING"}
    queries = read_json(DATA_DIR / "query-universe.json")
    competitors = read_json(DATA_DIR / "competitor-baseline.json")
    local_pack = read_json(DATA_DIR / "local-pack-baseline.json")
    decisions = read_json(DATA_DIR / "production-decisions.json")
    lines = [
        "# Big Mama Isolated SEO Intelligence and Integration Readiness",
        "",
        f"- Data validation: **{validation['status']}**",
        f"- Production integration ready: **{str(validation['productionReady']).lower()}**",
        f"- NAP consistency: **{nap['status']}**",
        f"- Menu consistency: **{menu['status']}**",
        f"- Website integrity: **{integrity['status']}**",
        f"- Query seed records: **{len(queries['queries'])}**",
        f"- Competitor observations: **{len(competitors['observations'])}**",
        f"- Local Pack observations: **{len(local_pack['observations'])}**",
        f"- Deployment ready: **{str(decisions['deploymentReady']).lower()}**",
        "- Website files modified by this system: **no**",
        "- Cache root: `reports/seo/.cache/`",
        "",
        "## Setup Required",
        "",
    ]
    lines.extend(f"- {item}" for item in validation["setupRequired"])
    lines.extend(["", "## Known Contradictions", ""])
    lines.extend(f"- `{item['productId']}`: {item['issue']}" for item in menu["contradictions"])
    lines.extend(["", "## External Integrations", "", "Google, DataForSEO, Firecrawl, backlink, Maps, review-platform, analytics, and account workflows remain `SETUP_REQUIRED` and were not invoked."])
    lines.extend(["", "## Integration Gate", "", "No website integration is permitted without `APPROVED — ALLOW SEO INTEGRATION INTO WEBSITE`."])
    result = atomic_write_text(REPORTS_DIR / "SEARCH-DATA-FOUNDATION-REPORT.md", "\n".join(lines))
    print_result(result)
    return 0
