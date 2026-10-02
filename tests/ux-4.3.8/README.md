# Bizora 4.3.8 — user-experience (UX) suite

Real Chromium, real app code, real IndexedDB, phone viewport **360×640** (touch, Android user-agent, Africa/Douala).
Path-independent: it serves the repository root on a free port. No outside network (fonts are blocked, like a weak connection).

```
python3 tests/ux-4.3.8/ux_suite.py          # all 13 layers, about 3 minutes
python3 tests/ux-4.3.8/ux_suite.py L3 L4    # chosen layers
```
Exit code 0 = every check passed. `WARN` lines are advisory and do not fail the run.

| Layer | What a shop owner is trying to do | Checks |
|---|---|---|
| L1 | First run: set up the business | wizard fits the phone, fields usable, empty name, setup remembered |
| L2 | Add products, see stock | add in 5 actions, blank/duplicate refused, lists fit 360 px |
| L3 | **Record a cash sale** | price auto-filled, total, change, receipt <300 ms, ≤9 actions, stock −3, triple-tap = one sale |
| L4 | **Record a credit sale** | customer required, deposit + "paid with", balance shown, debt ledger, stock limits |
| L5 | **Customer payment, find a balance** | search by name/phone, balance on the card, payment ≤6 actions, no method refused, overpayment |
| L6 | Receipt and WhatsApp | share buttons, number prompt, wa.me link and text, no "undefined" |
| L7 | **Add expense** | categories listed, ≤5 actions, bad amounts refused |
| L8 | Dashboard, reports, empty states | figures update at once, no NaN, quick actions open their form |
| L9 | Roles and access | cashier menu, permission enforced in code, not only the menu |
| L10 | Backup and restore | export file, restore on a clean install, corrupt file |
| L11 | Offline | cash sale, credit sale and expense with no internet |
| L12 | English / French | every page in FR at 360 px, receipt language, clipped buttons |
| L13 | Layout on a phone | every page without sideways scroll, bottom navigation, toast pile, modals fit |

**What this suite cannot tell you:** speed on a real 2 GB phone, finger comfort, sunlight readability and how a real shopkeeper
behaves. Use `MANUAL_ANDROID_UX.md` for that. The timings printed here come from a desktop CPU; treat them as a floor.

`FINDINGS_4.3.8.md` lists what the suite found on the audited build.
