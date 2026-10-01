# Bizora QA

Nothing in `qa/` is deployed. Only the runtime files listed in `netlify.toml` are published.

## Tools (run before every pull request)

| Command | Checks |
|---|---|
| `python3 qa/tools/check_syntax.py index.html` | Every inline `<script>` block passes `node --check`. Block 0 is a known false positive |
| `python3 qa/tools/protected_hash.py index.html qa/baselines/protected-4.3.8.json` | The 28 protected functions are byte-identical (exits 1 if any changed) |
| `node qa/tools/i18n_parity.js index.html` | EN/FR dictionaries have identical keys (exits 1 on mismatch) |

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

**Known limitation (backlog BZ-020, release 4.3.9):** these scripts were written in a temporary workspace. They still contain hard-coded paths (`/home/claude/...`, `/tmp/...`) and fixed ports, and some compare against older builds kept in folders outside this repository. Release 4.3.9 makes them path-independent and adds one `qa/run.js` entry point with a single pass/fail verdict. **Until then, treat them as reference material; do not delete or weaken them.**
