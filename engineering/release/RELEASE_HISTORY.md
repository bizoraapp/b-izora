# Release history

Newest first. Two states are kept apart on purpose:

- **Merged to `main`**: the code is in the `main` branch of this repository.
- **Live**: deployed to `bizora-cm.netlify.app` and verified there. Every push or merge to `main` is built by Netlify, so "live" depends on a successful Netlify production deploy, which is not the same thing as a merge.

Full change details are in the `DEVELOPER.md` changelog and in `engineering/audits/<version>/`.

| Version | Cache | Status (1 Oct 2026) | Summary |
|---|---|---|---|
| **4.3.8** | **v131** | **Merged to `main`** (PR #3, merge commit `f156eb6`). **Not confirmed live: production deployment is pending Netlify credits.** | Backup restore fix; explicit deposit payment method; "Not recorded" display; drawer note; deposit method on receipts. Also in this build: dashboard Smart Insights (code tagged v4.2.9) and WhatsApp PDF receipts opening the native share sheet directly (see `DEVELOPER.md` sections 11–12) |
| 4.3.7 | v130 | Included in 4.3.8 | Money controls: overpayment and refund approval, Expected Cash from physical cash only, drawer edit audit |
| 4.3.6 | v129 | Included in 4.3.8 | Credit-limit authorization and approvals |
| 4.3.5 | v128 | Included in 4.3.8 | Lock-screen recovery hardening |
| 4.3.4 | v127 | Included in 4.3.8 | Duplicate product names blocked |
| 4.3.3 | v126 | Included in 4.3.8 | Invoice controls, POS tax lock |
| 4.3.2 | v125 | Included in 4.3.8 | Owner approval for POS price changes |
| 4.3.1 | v124 | Included in 4.3.8 | Cashier access hardening, `viewHelp` permission |
| 4.3.0 | v123 | Included in 4.3.8 | Sidebar label "Start Selling" |
| **4.2.7** | **v120** | **Live** (last verified production version; previous cache v114) | i18n phases to 1,232 keys (EN/FR) |
| 4.2.1 | v114 | Earlier live | |
| 4.1.9 | v112 | Earlier live | |

## After 4.3.8: UX fixes UX-01 to UX-04 (merged to `main`, no version bump)

Merged to `main` on 2 Oct 2026 (PR #5, merge commit `9211ebc`, commits `8d454c8` and `5184d38`). `index.html` only. `APP_VERSION` stays 4.3.8, `CACHE_VERSION` stays v131, `IDB_VERSION` stays 8; no service-worker, database or timer change. **Not confirmed live**, like 4.3.8 itself. The next release number is Ngwe's decision.

- **UX-01:** the phone field on the first-run wizard now has the same style and height as the other fields.
- **UX-02:** the "No backup created yet" reminder is skipped on a fresh install, so it no longer covers Get Started. Existing users are unaffected.
- **UX-03:** Get Started refuses a blank business name with an inline message; Skip for now is unchanged.
- **UX-04:** the bottom navigation bar (Home / Sales / Credit / Inventory / More) now shows on phones (768 px and below), with French labels. It can be reverted alone with `git revert 5184d38`.

Checks recorded in PR #5: protected 28/28, EN/FR 1358/1358, UX suite 152/160 (the 5 targeted checks fixed; UX-05 to UX-10 remain open). UX-04 had not been tested on a real phone when it was merged.

## 4.3.8: version values

`APP_VERSION` 4.3.8 · `BUILD_NUMBER` 2026.10.01a · `CACHE_VERSION` v131 · `PREVIOUS_CACHE_VERSION` v120 · `IDB_VERSION` 8 (no schema change, no migration).

## 4.3.8: controlled release path from the 4.2.7 production baseline

1. **Production baseline:** `main` at `47bce18` matches live 4.2.7 (cache v120, previous v114, `IDB_VERSION` 8).
2. **`main` ran ahead of production.** On 1 Oct 2026 the 4.3.1–4.3.8 work (`430c4aa`, `b36bce6`, `0fc5374`) reached `main` directly, with the repository restructure on top (tip `9c91e16`), while Netlify could not deploy. The deployed files on `main` therefore no longer matched production.
3. **Candidate preserved.** The complete candidate is the tag `candidate-4.3.8` at `9c91e16`. The branch `release/4.3.8` was also left at `9c91e16` as a snapshot and is not moved.
4. **Production restored on `main`** (PR #2, `eb8dd14`, merge commit `ba9a225`): only `index.html` and `service-worker.js` were set back to their `47bce18` content, with a new commit and no history rewritten.
5. **4.3.8 re-applied as a reviewable diff** (PR #3, branch `release/4.3.8-prep`, commit `e4631d2`): the same two files, taken from the candidate tag, byte-identical to it. No other file changed.
6. **Checks recorded in PR #3:** syntax, protected functions 28/28 against the 4.3.8 baseline, EN/FR 1352/1352, the 4.3.x regression suites, backup and restore, offline, upgrades 4.2.7 → 4.3.8 and 4.3.7 → 4.3.8 with data identical, and performance at 1k–100k records. Known test-harness limitations and the existing BZ-009 issue are listed in the PR description. Real Android testing was done by Ngwe.
7. **Review and merge:** PR #3 was reviewed and merged into `main` (merge commit `f156eb6`, 1 Oct 2026, 15:30 UTC). Netlify built a deploy preview for the PR.
8. **Production deployment:** pending Netlify credits. No production deployment date or deployment ID exists yet; record them here when the deploy is verified on the live `service-worker.js`.

## Rollback chain

Archived, never deployed on their own: 4.2.8 (v121), 4.2.9 (v122), the separate 4.2.0 (v113) line. The dashboard Smart Insights code tagged v4.2.9 is part of the 4.3.8 build.

- **Once 4.3.8 is live:** devices that update hold `v131` + `v120` (the 4.2.7 cache is the rollback cache).
- **The next release after that** sets `PREVIOUS_CACHE_VERSION` to the cache that is live at that moment, checked on the live `service-worker.js`.
