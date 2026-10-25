# Big Mama Production Decision Form

Status: `USER_DECISION_REQUIRED`

Complete only the fields below. Do not provide credentials or verification tokens in this document.
External account access is not requested by this form.

## 1. LEGAL BUSINESS NAME

- Contract ID: `legal_business_name`
- Current status: `UNKNOWN`
- Why required: No legal entity name is approved; NOT_APPLICABLE is an allowed user decision.
- Affects: schema, legal-copy
- Decision/value:
- Evidence/source (when factual):

## 2. PRODUCTION ORIGIN

- Contract ID: `production_origin`
- Current status: `SETUP_REQUIRED`
- Why required: No production origin is verified.
- Affects: head-preview, schema-preview, sitemap-preview, robots-preview
- Decision/value:
- Evidence/source (when factual):

## 3. PREFERRED HOSTNAME

- Contract ID: `preferred_hostname`
- Current status: `SETUP_REQUIRED`
- Why required: www/non-www preference depends on the production origin.
- Affects: head-preview, schema-preview, sitemap-preview, robots-preview
- Decision/value:
- Evidence/source (when factual):

## 4. HTTPS STATUS

- Contract ID: `https_status`
- Current status: `SETUP_REQUIRED`
- Why required: No authorized production endpoint was tested.
- Affects: canonical, redirects, deployment
- Decision/value:
- Evidence/source (when factual):

## 5. HOSTING PLATFORM

- Contract ID: `hosting_platform`
- Current status: `UNKNOWN`
- Why required: Repository evidence does not establish the final hosting platform.
- Affects: deployment, redirects, 404
- Decision/value:
- Evidence/source (when factual):

## 6. DEPLOYMENT BRANCH

- Contract ID: `deployment_branch`
- Current status: `UNKNOWN`
- Why required: No deployment branch is approved.
- Affects: deployment, ci
- Decision/value:
- Evidence/source (when factual):

## 7. CANONICAL HOME URL

- Contract ID: `canonical_home_url`
- Current status: `SETUP_REQUIRED`
- Why required: Cannot be derived until origin and hostname are approved.
- Affects: head-preview, schema-preview, sitemap-preview, robots-preview
- Decision/value:
- Evidence/source (when factual):

## 8. PUBLIC EMAIL OR EXPLICIT EMAIL REMOVAL

- Contract ID: `public_email`
- Current status: `UNKNOWN`
- Why required: The current .example address is a placeholder and is not production eligible.
- Affects: visible-content, contact, schema
- Decision/value:
- Evidence/source (when factual):

## 9. HOLIDAY-HOURS OPERATING POLICY

- Contract ID: `holiday_hours_policy`
- Current status: `SETUP_REQUIRED`
- Why required: No holiday or exceptional-hours owner is defined.
- Affects: visible-content, schema, open-now, operations
- Decision/value:
- Evidence/source (when factual):

## 10. PRIMARY BUSINESS CATEGORY

- Contract ID: `primary_business_category`
- Current status: `SETUP_REQUIRED`
- Why required: Restaurant is supported, but the operational primary profile category requires approval.
- Affects: schema, business-profiles, metadata
- Decision/value:
- Evidence/source (when factual):

## 11. PRICE-RANGE DECISION

- Contract ID: `price_range`
- Current status: `UNKNOWN`
- Why required: No supportable public price range is present; removal is allowed.
- Affects: schema, visible-content
- Decision/value:
- Evidence/source (when factual):

## 12. GOOGLE BUSINESS PROFILE URL OR PLACE IDENTIFIER

- Contract ID: `google_business_profile`
- Current status: `UNKNOWN`
- Why required: A Maps URL is observed, but profile ownership/current identity is not externally verified.
- Affects: schema, local-search, reviews
- Decision/value:
- Evidence/source (when factual):

## 13. VERIFIED SOCIAL-PROFILE URLS

- Contract ID: `social_profiles`
- Current status: `UNKNOWN`
- Why required: No official social profiles are verified.
- Affects: sameAs, social, local-search
- Decision/value:
- Evidence/source (when factual):

## 14. APPROVED SOCIAL IMAGE

- Contract ID: `approved_social_image`
- Current status: `SETUP_REQUIRED`
- Why required: No absolute production image URL is approved.
- Affects: open-graph, social-preview, schema
- Decision/value:
- Evidence/source (when factual):

## 15. BIG TOKYO STATUS

- Contract ID: `big_tokyo_status`
- Current status: `CONTRADICTORY`
- Why required: COMING SOON conflicts with enabled order actions.
- Affects: menu, schema, answers, ordering
- Decision/value:
- Evidence/source (when factual):

## 16. DISPLAYED RATING EVIDENCE OR REMOVAL

- Contract ID: `displayed_rating`
- Current status: `UNKNOWN`
- Why required: The displayed value lacks approved source/date/count evidence.
- Affects: visible-content, schema, reviews
- Decision/value:
- Evidence/source (when factual):

## 17. REVIEW-COUNT EVIDENCE OR REMOVAL

- Contract ID: `review_count`
- Current status: `UNKNOWN`
- Why required: No current verified aggregate review count is approved.
- Affects: visible-content, schema, reviews
- Decision/value:
- Evidence/source (when factual):

## 18. LANGUAGE STRATEGY

- Contract ID: `language_strategy`
- Current status: `SETUP_REQUIRED`
- Why required: The current declaration is observed; production architecture is not approved.
- Affects: html-lang, content, canonical, hreflang, sitemap
- Decision/value:
- Evidence/source (when factual):

## 19. SEARCH-CRAWLER POLICY

- Contract ID: `search_crawler_policy`
- Current status: `SETUP_REQUIRED`
- Why required: Search indexing crawler policy requires explicit approval.
- Affects: robots, indexing
- Decision/value:
- Evidence/source (when factual):

## 20. AI-SEARCH/ANSWER CRAWLER POLICY

- Contract ID: `ai_search_crawler_policy`
- Current status: `SETUP_REQUIRED`
- Why required: AI search access must be decided separately from training.
- Affects: robots, ai-search
- Decision/value:
- Evidence/source (when factual):

## 21. AI-TRAINING CRAWLER POLICY

- Contract ID: `ai_training_crawler_policy`
- Current status: `SETUP_REQUIRED`
- Why required: AI training consent requires an explicit decision.
- Affects: robots, ai-training
- Decision/value:
- Evidence/source (when factual):

## 22. UNKNOWN-CRAWLER POLICY

- Contract ID: `unknown_crawler_policy`
- Current status: `SETUP_REQUIRED`
- Why required: Unknown-crawler default policy is not approved.
- Affects: robots, security
- Decision/value:
- Evidence/source (when factual):

## 23. COOKIE/ANALYTICS CONSENT DECISION

- Contract ID: `analytics_consent`
- Current status: `SETUP_REQUIRED`
- Why required: No consent and privacy architecture is approved.
- Affects: analytics, privacy, legal-copy
- Decision/value:
- Evidence/source (when factual):

## 24. PUBLIC LEGAL COPY STATUS

- Contract ID: `public_legal_copy`
- Current status: `SETUP_REQUIRED`
- Why required: Legal copy remains a placeholder.
- Affects: visible-content, privacy, analytics
- Decision/value:
- Evidence/source (when factual):

## 25. CONTACT CTA DECISION

- Contract ID: `contact_cta`
- Current status: `SETUP_REQUIRED`
- Why required: Phone/email/directions contact behavior requires production approval.
- Affects: visible-content, measurement
- Decision/value:
- Evidence/source (when factual):

## 26. ORDER CTA DECISION

- Contract ID: `order_cta`
- Current status: `SETUP_REQUIRED`
- Why required: Current provider actions are observed but not approved as the production contract.
- Affects: visible-content, measurement, ordering
- Decision/value:
- Evidence/source (when factual):

## 27. ANALYTICS PROPERTY STATUS

- Contract ID: `analytics_property`
- Current status: `SETUP_REQUIRED`
- Why required: No authorized analytics property is identified.
- Affects: analytics, measurement
- Decision/value:
- Evidence/source (when factual):

## 28. SEARCH CONSOLE STATUS

- Contract ID: `search_console`
- Current status: `SETUP_REQUIRED`
- Why required: No account or property access is authorized.
- Affects: verification, sitemap, measurement
- Decision/value:
- Evidence/source (when factual):

## 29. BING WEBMASTER STATUS

- Contract ID: `bing_webmaster`
- Current status: `SETUP_REQUIRED`
- Why required: No account or site access is authorized.
- Affects: verification, sitemap, measurement
- Decision/value:
- Evidence/source (when factual):

## 30. INDEXNOW STATUS

- Contract ID: `indexnow`
- Current status: `SETUP_REQUIRED`
- Why required: No host, key, endpoint workflow, or authorization is approved.
- Affects: key, submission, ci
- Decision/value:
- Evidence/source (when factual):

## 31. BUSINESS PROFILE MANAGEMENT STATUS

- Contract ID: `business_profile_management`
- Current status: `SETUP_REQUIRED`
- Why required: Profile ownership/access has not been established.
- Affects: google-business-profile, local-search, measurement
- Decision/value:
- Evidence/source (when factual):

## Validation Gate

Answers will be checked for URL validity, internal consistency, source support, crawler-policy separation, privacy implications and conflicts with protected website facts.

Website integration will remain blocked after answer validation until the exact phrase `APPROVED — ALLOW SEO INTEGRATION INTO WEBSITE` is supplied.
