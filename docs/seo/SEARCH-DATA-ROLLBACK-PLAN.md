# Search Data Rollback Plan

The approved foundation created only previously absent isolated roots. No website backup was needed because no website file is writable by this system.

Rollback procedure:

1. Stop running search-data processes.
2. Verify the resolved rollback targets are exactly `seo/`, `scripts/seo/`, `docs/seo/`, and `reports/seo/` under this repository.
3. Preserve any user-added evidence or export it separately if requested.
4. Remove only the approved isolated roots.
5. Recompute protected website hashes and confirm they still match the pre-implementation manifest.

Never use Git reset, restore `.approved-baseline/`, or overwrite a changed protected file automatically.
