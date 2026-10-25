# Big Mama Website — STRICT Codex Control System

You are working on the Big Mama Burgers n’ Fries website.

The user has explicitly stated that you must do **ONLY** what they ask.  
This project has an approved visual baseline. Your default job is to preserve it.

## Non-negotiable operating mode

You are not allowed to freely redesign, refactor, modernize, improve, optimize, or reinterpret the website.

You must follow the user’s request literally and narrowly.

If the user asks for one change, perform only that change.

If a change may affect layout, navigation, menu, visual hierarchy, animation behavior, assets, SEO metadata, or JavaScript behavior, you must stop and ask for approval first.

## Approval gate

Before editing any file, you must provide:

1. Exact file-level plan.
2. Exact selectors/components/sections affected.
3. Why each change is necessary.
4. Business purpose of each change.
5. Risk assessment.
6. Confirmation that unrelated sections will not be touched.
7. Whether any dependency/library is needed.
8. A rollback plan.

You may only edit files after the user replies with an explicit approval phrase such as:

`APPROVED — PROCEED`

If the user does not explicitly approve, do not edit.

## Absolute restrictions

Do not:
- change the main menu layout unless explicitly requested,
- change the MENU nav button size/style unless explicitly requested,
- change the category tabs unless explicitly requested,
- hide menu items,
- add huge blank spaces,
- redesign the hero,
- replace brand typography,
- rewrite copy broadly,
- add fake reviews,
- add fake ratings,
- invent phone numbers,
- invent Google Maps links,
- add new animation libraries,
- add Three.js / GSAP / Anime.js / Lottie / Framer Motion unless explicitly approved,
- modify assets unless explicitly requested,
- touch `.approved-baseline/` except for reading or restoring,
- touch `.codex-skills/`, `codex-prompts/`, or `docs/` unless explicitly requested.

## Baseline restore system

Approved baseline copies exist in:

`.approved-baseline/`

These are the clean source-of-truth copies for:
- `index.html`
- `styles.css`
- `app.js`
- `README.md`

If damage occurs, restore from `.approved-baseline/`.

If asked to restore original design, inspect `.approved-baseline/` first and use the smallest possible restore.

## Change-control workflow

For every task:

### Phase 1 — Inspect only
Do not edit. Inspect the relevant files and current behavior.

### Phase 2 — Plan only
Return a precise file-level plan. Wait for explicit approval.

### Phase 3 — Implement narrowly
After approval, edit only the approved files and sections.

### Phase 4 — Verify
Check the exact requested outcome. Do not add extra improvements.

### Phase 5 — Report
Summarize:
- files changed,
- sections changed,
- why each change was necessary,
- what was not touched,
- manual test checklist,
- rollback instructions.

## Big Mama brand direction

Preserve:
- orange neon identity,
- white/orange premium contrast,
- bold rounded Big Mama typography,
- food-first visual energy,
- existing layout unless asked,
- existing premium navigation shape,
- existing menu/category structure unless asked,
- mobile performance.

## Motion rules

Use CSS first.

Allowed only when explicitly requested:
- subtle neon pulse,
- loader polish,
- small menu-card micro-interaction,
- sticky mobile CTA animation,
- scroll reveal refinement.

Do not add animation just because a skill exists.

Every motion change must support one of:
- ordering,
- trust,
- appetite,
- CTA guidance,
- brand memorability.

## SEO rules

SEO changes are allowed only when explicitly requested.

Never add fake:
- aggregateRating,
- reviews,
- phone number,
- address,
- opening hours,
- Google Maps link.

Use real placeholders only inside code comments/TODOs when missing.

## Runtime library policy

Default: no new runtime libraries.

If you think a library is needed, you must justify:
1. why CSS/vanilla JS is not enough,
2. exact library,
3. exact file/package change,
4. performance impact,
5. rollback plan.

Wait for explicit approval.

## Skills usage

Local skills are stored under `.codex-skills/`.

Skills are guidance, not permission.

Using a skill never overrides the approval gate.

If a skill suggests broad improvements, ignore broad parts and apply only the exact user-requested change.

## Emergency rule

If you are uncertain, stop and ask.

Never guess.
Never silently “improve”.
Never perform uncontrolled changes.

<!-- BEGIN:nextjs-agent-rules -->

# This is NOT the Next.js you know

This version has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` (resolved from this file's directory; in monorepos the `next` package may not be visible from the repo root) before writing any code. Heed deprecation notices.

This block is written and re-added by `next dev` — verify at `node_modules/next/dist/server/lib/generate-agent-files.js`. Removing it from a diff only re-creates the uncommitted change; committing it with your work keeps the tree clean.

<!-- END:nextjs-agent-rules -->
