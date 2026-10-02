# Bizora QA

Nothing in `tests/` is deployed. Only the runtime files listed in `netlify.toml` are published.

## Tools (run before every pull request)

| Command | Checks |
|---|---|
| `python3 tests/tools/check_syntax.py index.html` | Every inline `<script>` block passes `node --check`. Block 0 is a known false positive |
| `python3 tests/tools/protected_hash.py index.html auto` | The 28 protected functions are byte-identical to the baseline for this `APP_VERSION` (`tests/baselines/protected-<version>.json`, or the newest older one); exits 1 on any change not listed in `tests/approved_protected_changes.txt` |
| `node tests/tools/i18n_parity.js index.html` | EN/FR dictionaries have identical keys (exits 1 on mismatch) |

## Regression suites (`suites-4.3.x/`)

These are the real-browser suites behind releases 4.3.3–4.3.8: Playwright with Python and Chromium, about 700 checks. Recorded results for the audited 4.3.8 build:

| Suite | File(s) | Result |
|---|---|---|
| 4.3.8 payment-method integrity | `t438.py` | 97/97 |
| Backup restore | `restore438.py` + `seed438.js` | 25/25 |
| Backup compatibility (4.2.7 / 4.3.7 backups) | `compat438.py` | 4/4 |
| Offline | `offline438.py` | 6/6 |
| 4.3.7 money controls (adapted for 4.3.8) | `t437v438.py` (base helpers in `t437.py`) | 98/98 |
| 4.3.2–4.3.6 regression | `fin_*.py` | 390/390 + 3 value-reporting suites |
| Upgrade | `upgrade_prod.py` (4.2.7→), `upgrade438.py` (4.3.7→) | data identical |
| Performance | `perf438.py`, `perf438b.py` | within noise of the previous release |
| In-app self-tests | `devsuite437.py` | 30 pass (same 1 known fail as 4.3.6) |

**Known limitation (backlog BZ-020, release 4.3.9):** these scripts were written in a temporary workspace. They still contain hard-coded paths (`/home/claude/...`, `/tmp/...`) and fixed ports, and some compare against older builds kept in folders outside this repository. Release 4.3.9 makes them path-independent and adds one `tests/run.js` entry point with a single pass/fail verdict. **Until then, treat them as reference material; do not delete or weaken them.**

## UX suite (`ux-4.3.8/`)

Phone-viewport (360×640) user-experience checks across 13 layers, plus a manual script for a real Android phone.
Run `python3 tests/ux-4.3.8/ux_suite.py`. Results on the audited 4.3.8 build: 147/160 pass; the 13 failures are 10 display/flow
problems listed in `tests/ux-4.3.8/FINDINGS_4.3.8.md` (UX-01 to UX-10), proposed for the backlog.
