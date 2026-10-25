# Search Measurement Plan

Status: planning only. No analytics code is installed and no external account was accessed.

`seo/measurement-plan.json` defines future conversion-event and search-measurement contracts. Potential sources remain credential- and authorization-gated.

## Measurement Families

- Search Console query, country, device, and date measurements.
- Local Pack and geo-grid rank-or-presence observations.
- Aggregate review-request and response operations.
- AI-search brand mention and citation observations.
- Field Core Web Vitals from CrUX or PageSpeed Insights.
- Approved interaction events for ordering, providers, directions, telephone, reviews, menu categories, maps, and contact actions.

## Evidence Rules

Set numerical targets only after a verified baseline. Keep manual, API, laboratory, field, account, and provider evidence separate. Report LCP, INP, and CLS only from sources that provide them; TBT must never be relabeled as INP.

The accepted search-data performance baseline must not be replaced automatically. Phase verification must write a separate report and compare without promotion unless a human approves baseline replacement.

Measurement must honor consent, minimization, retention, access control, and credential redaction. Do not collect order details, reviewer identity, or customer personal data in SEO reports.
