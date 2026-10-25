# SEO/AEO Data Contract

Version: 1.0.0 with backward-compatible Phase 2 additions.

The `seo/` directory is the isolated source of truth for search intelligence and integration readiness. It is not a browser runtime, CMS, production API, deployment package, or credential store.

## Status Vocabulary

- `VERIFIED`: confirmed by matching approved business input and repository evidence.
- `OBSERVED`: directly present in a source but not independently verified.
- `INFERRED`: a documented planning conclusion, never a production fact.
- `UNKNOWN`: unavailable and represented as `null`.
- `SETUP_REQUIRED`: blocked until a required fact, credential, evidence source, or approval exists.
- `NOT_APPLICABLE`: intentionally excluded.

Only `VERIFIED` fields may be considered for future production integration after separate approval. Unknown optional values are omitted. Unknown production-required values block readiness.

## Phase 2 Contracts

- `production-decisions.json` owns production origin, social-image, crawler, and website-integration gates.
- `query-universe.json`, `keyword-clusters.json`, and `intent-map.json` own inferred query planning without metrics.
- `competitor-baseline.json` and `local-pack-baseline.json` own future observation schemas; they contain no fabricated observations.
- `review-operations.json` owns legitimate request, response, escalation, and aggregate measurement rules.
- `entities.json` and `schema-policy.json` own preview entity eligibility and omissions.
- `answer-data.json` owns source-backed answer records and prohibits hidden publication.

## Determinism And Isolation

JSON is UTF-8, key-sorted when generated, stably ordered, and newline-normalized. Atomic writes occur only in approved isolated roots. Cache is limited to `reports/seo/.cache/`. Semantic outputs contain no run timestamps; execution and evidence reports may contain UTC timestamps.

Prices, Offers, availability, ratings, review counts, allergens, nutrition, competitors, rankings, search volume, CPC, click estimates, traffic potential, backlinks, citations, account access, and credentials must remain null or empty unless documented evidence supports them.
