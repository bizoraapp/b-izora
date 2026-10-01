# CLAUDE.md — Bizora engineering contract

Read this whole file before touching anything. It is the contract between the product owner (Ngwe), the product manager and you (Claude Code).

**Then read the docs your task touches:**

| Doc | Read it when |
|---|---|
| `docs/product/PRODUCT.md` | Always, once per session: users, modules, roles, money vocabulary, workflows, design principles |
| `engineering/BUG_HISTORY.md` | Before changing any area. Every past bug, its root cause and the rule it left behind |
| `docs/architecture/I18N.md` | Before adding or changing any visible text (EN/FR rules, French typography, glossary) |
| `engineering/decisions/` (ADR files) | Before proposing a change to existing behaviour. Decided questions stay closed |
| `docs/architecture/PRO-*.md`, `docs/product/PRO-00_Product_Constitution.md`, `docs/implementation/PRO-12_*.md` | When present: the **Bizora Pro** target architecture. They describe the future product, **not** the live app. Never use them to justify changing Bizora Basic code; if they conflict with the live code or `docs/product/PRODUCT.md`, stop and report |
| `engineering/release/RELEASE_CHECKLIST.md` | Before declaring any release ready |
| `engineering/audits/<version>/` | For the plan, implementation report and audit of a past release |
| `tests/README.md` | Before testing |

Bizora is a **production** app. Real shops in Cameroon record their sales, debts and cash in it every day, often offline, on 2–4 GB Android phones. A broken release can lose a shop's records or show the wrong cash figure. **Being careful matters more than being fast.**

---

## 1. Deployment safety (read first)

- **Every push or merge to `main` deploys to production** (GitHub → Netlify) and reaches every user.
- **You never push to `main`, merge into `main`, force-push, rewrite history, delete branches or tags, or run any deploy command.** Ngwe merges, and only after a review and a real-Android test.
- Work only on a branch: `release/<version>` for a release, `fix/<short-name>` or `investigate/<short-name>` otherwise. Open a pull request. Netlify builds a **deploy preview** for it; that preview URL is what Ngwe tests on the phone.
- Only these files are deployed (`netlify.toml` copies exactly these into `dist/`): `index.html`, `service-worker.js`, `manifest.json`, `offline.html`, `icons/`. **If you add a file the app needs at runtime, you must add it to the `netlify.toml` allowlist and say so in the PR.** Everything else (this file, `docs/`, `engineering/`, `tests/`) is never published.
- **This repository is public.** Never commit secrets, real customer data, backups, exported JSON or ZIP builds. Never describe an unfixed vulnerability in detail in a commit message or PR. Say "security fix, details in the project tracker" instead.

### Automatic guardrails (hooks in `.claude/`)

These run on every session. **Never disable, bypass or edit them**; changing `.claude/` asks Ngwe's permission.
- **Session start:** prints the branch, versions and these rules.
- **Before any shell command:** blocks pushes to `main`, force or delete pushes, merges into `main`, history rewrites (`reset --hard`, `rebase`), branch/tag deletion, deploy tools and hosting APIs, recursive deletes, and commits of ZIPs, backups or secrets.
- **Before any file edit:** blocks edits while on `main` and inside `.git`.
- **After editing `index.html`:** runs the syntax check, the 28 protected-function hashes and EN/FR parity; it also warns about known traps (`.toISOString()` date keys, hard-coded `method:'cash'`, new timers, `S.set` on large stores, translated text in audit entries).
- **Before you finish:** re-runs the checks if app files changed.

If a hook blocks you, **stop and report**. Don't look for another way to run the command. If a protected function must change, that needs Ngwe's explicit approval: he adds its name to `tests/approved_protected_changes.txt`, and you say so in the PR.

## 2. How work is done (non-negotiable)

1. **Investigate first, read-only.** Every task starts by reading the real code. Report findings with exact function names and line numbers. **No code is written until the scope is explicitly approved.**
2. **Approved scope only.** Change exactly what was approved. If you find another problem, report it as a separate finding. Never fix it "while you're there".
3. **Explain before coding:** the existing code involved, the files and functions you will change, what you will reuse, any data changes, the migration plan, why existing behaviour stays safe, and the risks.
4. **Checkpoint:** create the branch from the approved base and record the base commit before editing.
5. **Validate** (section 7) and **report** with exact counts: never "all tests passed" without numbers.
6. **Stop and report, never improvise,** when:
   - existing calculations disagree with each other;
   - historical financial results would change;
   - a database migration looks necessary;
   - the scope would grow;
   - an existing approval or security control would need changing;
   - a regression appears that is unrelated to your change;
   - real-device behaviour contradicts browser tests.
7. When you make a mistake, go back to the checkpoint and redo the work cleanly. Don't patch forward on top of a bad change.

## 3. Architecture (what exists — extend it, never rebuild it)

**Release state:** live production = **4.2.7 (cache v120)**. The audited **4.3.8** (cache v131, `PREVIOUS_CACHE_VERSION` v120) arrives through the `release/4.3.8` pull request. Rules in sections 4–5 that name 4.3.8 functions apply once that PR is merged. Before any work, check which version `main` actually contains (`APP_VERSION` in `index.html`).

- **Single-file app:** `index.html`, about 19,000 lines of HTML, CSS and vanilla JavaScript. No framework, no bundler, no npm dependencies at runtime. **Do not introduce React, TypeScript, build tools or libraries.**
- **Storage:** IndexedDB database `CreditBossDB`, **`IDB_VERSION = 8`**, mirrored in memory (`MEM`). All reads and writes go through `S.get / S.set / S.add / S.update / S.remove` and `S.obj / S.setObj`. **Never change `S.set()` globally.** Key → store: `sales→creditSales`, `payments→repayments`, `posSales`, `customers`, `products`, `expenses`, `creditLedger`, `employees`, `auditLog→auditLogs`, `activities`, `stockMovements`; settings-like objects (including `cashDrawer`) are kept in `settings`.
- **PWA:** `service-worker.js` with `CACHE_VERSION` and `PREVIOUS_CACHE_VERSION` (the rollback cache). The update waits for the user to accept it. Offline operation is a core requirement.
- **Languages:** English and French (`I18N_DICT.en` / `.fr`, `t()`, `tf()`, `data-i18n`). Every new visible string needs **both** languages.
- **Access control:** `Auth` (Owner or employee roles cashier, storekeeper, sales_rep, supervisor; `Auth.can(perm)`). `OwnerApproval` gives single-use Owner-password approvals; never weaken or reuse them. **Permission checks belong inside the function that writes data, not only on the button.**

## 4. Financial rules (correctness over convenience)

- **Use the existing sources of truth; never re-derive them:** `invBalance`, `invPaidAmt`, `custDebt`, `custPaid`, `custInvoiced`, `custCreditBalance`, `computeExpenseTotals`, `computeRealizedProfit`, `buildProfitIndex`, `computeNetProfit`, `computeDrawerCash`.
- **Payment methods:**
  - `payment.method === 'cash'` means **physical cash**.
  - `posSales.type === 'cash'` only means "paid now" and says **nothing** about the method.
  - New payments must use the canonical `PAYMENT_METHODS` list (`DEPOSIT_METHODS` for deposits), checked with `isPaymentMethod()` **inside the save function**.
  - Never default, guess or convert a method to cash.
- **Never rewrite historical records** to make new logic work. Old records with a missing or unknown method are shown as "Not recorded" and left out of Expected Cash.
- Never allow incorrect balances, incorrect totals, duplicate transactions or data loss. Every money-affecting action writes an audit entry: who, what, amount, method, before→after.
- **Stored values are never translated:** role keys, permission keys, statuses, methods and audit text stay in canonical English.

## 5. Protected code

These functions must stay **byte-identical** unless Ngwe explicitly approves a change. They are checked with `python3 tests/tools/protected_hash.py index.html auto`, which picks `tests/baselines/protected-<APP_VERSION>.json` (or the newest older one). After a release with an approved change is merged, a new baseline is committed for that version and the approval list is emptied:

`computeRealizedProfit, buildProfitIndex, computeExpenseTotals, computeNetProfit, computeProductSalesAggregates, collectLossRecords, computeShortageChainStatus, filterCollection, loadCollection, renderCollInsights, filterCustomers, drawAllCharts, loadDashboard, custDebt, invBalance, invStatus, stockStatus, openLossRegisterView, filterLossRegister, loadProducts, renderProdTable, saveProduct, resetProdForm, go, shareReceiptPdfWhatsApp, downloadReceipt, printReceipt, _generateReceiptPdfBlob`

## 6. Versioning (every release)

- **Version numbers:** the patch digit runs 0–9, then the minor version goes up: 4.3.9 → 4.4.0. Never 4.3.10.
- **Update:** `APP_VERSION`, `BUILD_NUMBER`, `CACHE_VERSION` (+1), the `DEVELOPER.md` header and changelog.
- **Database:** `IDB_VERSION` changes **only** for an approved schema change, which needs a tested, reversible migration.
- **`PREVIOUS_CACHE_VERSION` = the cache that is LIVE right now.** Check it on the live `service-worker.js` before release; never assume a candidate was deployed.

## 7. Validation before any PR is ready

1. `python3 tests/tools/check_syntax.py index.html`. Every `<script>` block passes `node --check`; block 0 is a known false alarm (a `<script>` tag inside an HTML comment).
2. `python3 tests/tools/protected_hash.py index.html auto`: 28/28 unchanged against the baseline for the current version (`tests/baselines/`), except names Ngwe approved in `tests/approved_protected_changes.txt`.
3. `node tests/tools/i18n_parity.js index.html`: EN and FR key counts equal, none missing.
4. **Diff confinement:** every changed line belongs to the approved scope. List the changed functions.
5. **Regression suites** in `tests/suites-4.3.x/` (Playwright + Chromium against a local HTTP server; IndexedDB needs a real origin). New behaviour gets new tests; existing tests are never weakened. If an existing test must change because of an approved behaviour change, report the exact diff and why.
6. **Performance:** consider 1k, 10k, 50k and 100k transactions for anything that processes data. Report complexity, scans, memory and low-end Android impact. **No new timers, polling or startup scans.**
7. **Mobile:** a 360 px layout check, plus EN and FR.
8. **Upgrade safety:** data stays identical after upgrading from the live version.

## 8. Known traps

- Modals hide with `opacity` and the class `.on`, not `display:none`. Test `classList.contains('on')`. Toasts can block clicks.
- `parseFloat`/`parseInt` are wrapped globally to strip thousands commas (`num-fmt` fields).
- `confirm2()` displays **plain text** (`textContent`); HTML in its message prints literally.
- Passing an object's method on its own (e.g. `ValidationService.validateX` stored in a variable) loses `this`. Call it as `ValidationService.validateX(rec)`.
- `let`/`const` used before their declaration line throw (temporal dead zone). Keep new top-level declarations above their first runtime use.
- The first-run wizard is controlled by saved IndexedDB state; check with `?devreset=1` before blaming code.
- Searching the code with grep alone has given false conclusions before. Confirm with the real code running in a browser.

## 9. Product decisions already made (don't reopen without being asked)

See `engineering/decisions/` (one ADR file per decision). Example: sale reversal keeps its current deletion behaviour (decided 2026-10-01). Open items and priorities are in the PM's backlog. Work only on what a brief assigns.

## 10. Report format (end of every task)

Branch and base commit · files changed · functions changed · what was done · data/migration impact · test results with exact counts (new, regression, EN/FR, 360 px, offline, upgrade, performance) · diff-confinement statement · open risks · **"Not merged. Not deployed."**
