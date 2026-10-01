# Release checklist

A release is **ready** only when every box is ticked with real numbers. Claude Code prepares and reports; Ngwe tests on a phone, merges and deploys.

## 1. Before coding
- [ ] Scope approved in writing (brief or Ngwe's message); read-only investigation reported first
- [ ] Branch `release/<version>` created from the approved base; base commit recorded; checkpoint tag if Ngwe asked
- [ ] `docs/product/PRODUCT.md`, `engineering/BUG_HISTORY.md` and relevant ADRs read

## 2. Versions
- [ ] `APP_VERSION`, `BUILD_NUMBER` updated (patch digit 0–9, then minor: 4.3.9 → 4.4.0)
- [ ] `CACHE_VERSION` +1 in `service-worker.js`
- [ ] `PREVIOUS_CACHE_VERSION` = the cache **live right now**, checked on `https://bizora-cm.netlify.app/service-worker.js`. Never assumed
- [ ] `IDB_VERSION` unchanged unless a tested, reversible migration was approved
- [ ] `DEVELOPER.md` header and changelog updated; `engineering/release/RELEASE_HISTORY.md` entry added

## 3. Automated checks (exact counts in the PR)
- [ ] `python3 tests/tools/check_syntax.py index.html`
- [ ] `python3 tests/tools/protected_hash.py index.html auto`: 28/28, or only names Ngwe approved in `tests/approved_protected_changes.txt`
- [ ] `node tests/tools/i18n_parity.js index.html`: EN = FR, 0 missing
- [ ] Diff confinement: every changed line belongs to the approved scope; changed functions listed
- [ ] New tests for the new behaviour; regression suites in `tests/suites-4.3.x/` unchanged and passing (run sequentially)
- [ ] Upgrade test from the **live** version: data identical
- [ ] Backup export from the old version restores into the new one
- [ ] Offline test; 360 px layout in EN and FR
- [ ] Performance at 1k / 10k / 50k / 100k transactions where data is processed (complexity, scans, memory)

## 4. Audit (separate pass, audit only)
- [ ] Release audit written to `engineering/audits/<version>/` (what changed, evidence, risks, verdict)
- [ ] No unrelated change, no second calculation engine, no historical record rewritten

## 5. Ngwe
- [ ] Pull request opened; Netlify deploy preview built
- [ ] Real Android test on the preview (install, update from the live version, the changed flows, offline, close and reopen)
- [ ] `main` merged by Ngwe → live site shows the new version and cache; update banner appears on an old device; existing data intact

## 6. After deploy
- [ ] Baseline committed: `tests/baselines/protected-<version>.json`; `tests/approved_protected_changes.txt` emptied
- [ ] Watch the first week for user reports; rollback = redeploy the previous version (its cache is kept on updated devices)
