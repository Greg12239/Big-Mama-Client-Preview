# Website Isolation Policy

The search-data system may read protected website files but may never write to them.

Permitted output roots:

- `seo/`
- `scripts/seo/`
- `docs/seo/`
- `reports/seo/`

The root `.seo-cache/` path is prohibited. All cache data belongs under `reports/seo/.cache/`.

Every writer resolves and validates its destination, rejects path traversal and reparse-point escape, writes a same-directory temporary file, validates and flushes it, replaces atomically, and verifies the destination hash.

Protected website integration remains blocked until the exact phrase:

`APPROVED — ALLOW SEO INTEGRATION INTO WEBSITE`

Performance changes require the separate phrase:

`APPROVED — ALLOW PERFORMANCE CHANGES TO WEBSITE`
