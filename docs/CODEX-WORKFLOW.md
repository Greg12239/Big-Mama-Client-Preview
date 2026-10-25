# Big Mama Codex Workflow

## Absolute rule

Codex must not edit until you approve the plan with:

`APPROVED — PROCEED`

## Start

Paste this into Codex:

```text
Read AGENTS.md first.

Open codex-prompts/00_START_HERE_STRICT_MODE.md and follow it.

Do not edit any files.
```

## For any new task

Use:

`codex-prompts/01_SAFE_TASK_TEMPLATE.md`

Replace the task placeholder with your exact request.

## If Codex breaks something

Use:

`codex-prompts/02_RESTORE_APPROVED_BASELINE.md`

or, if only menu broke:

`codex-prompts/03_MENU_RESTORE_ONLY.md`

## Approved baseline

Original source files are backed up in:

`.approved-baseline/`

## What this folder is designed to prevent

- uncontrolled redesign,
- broken menu,
- oversized nav buttons,
- fake SEO data,
- unnecessary libraries,
- broad refactors,
- editing without permission.
