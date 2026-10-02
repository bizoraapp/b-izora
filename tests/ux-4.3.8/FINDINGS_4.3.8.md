# UX findings on Bizora 4.3.8 (build 2026.10.01a)

Run: 160 checks, **147 pass, 13 fail** (10 distinct problems), 5 advisory warnings. Nothing here loses data or changes money.
All are display or flow problems; none is a reason to un-approve the 4.3.8 audit, but UX-01 and UX-02 hurt the very first minute a new shop spends in the app.
Each finding is a **proposal for the backlog**, not a fix. Nothing was changed in `index.html`.

| ID | Severity | Where | What the user sees | Likely cause (to confirm) |
|---|---|---|---|---|
| UX-01 | High | First run | Phone field is 19 px tall, square, tiny text; the other two fields are 39 px, rounded | `input[type=tel].fc` is missing from the `.fc` selector lists (lines ~265, 268, 438) |
| UX-02 | High | First run | The "No backup created yet" toast sits on top of the **Get Started** button; the user must wait or scroll | Toast rack overlaps the wizard footer on a 640 px screen |
| UX-03 | Medium | First run | Tapping Get Started with an empty name succeeds: shop name saved as "", receipts print "BIZORA" or blank | `FirstRunWizard.complete()` has no name check |
| UX-04 | Medium | Home (phones) | The bottom navigation (Home / Sales / Credit / Inventory / More) never appears | line 820 `display:none` comes after the line 749 media rule |
| UX-05 | Medium | Receipt in French | "Amount Paid", "Change", "Thank you for your business!" stay English | hard-coded strings at ~14600, 14774, 14582 (footer default); `lbl_change` exists in FR |
| UX-06 | Medium | Calendar | Saturday and Sunday columns and the Next button are cut off; page scrolls sideways | 7-column grid wider than 360 px |
| UX-07 | Medium | Dashboard after a sale | Page becomes 476 px wide; the activity feed is wider than the screen | `.act-item` content not allowed to shrink |
| UX-08 | Medium | Settings (FR) | Page is 403 px wide; buttons run off the right edge | long French button labels do not wrap |
| UX-09 | Low | French POS | "Terminer la Vente et Imprimer le Reçu" is clipped (BZ-015, already known) | long label, fixed width |
| UX-10 | Low | Toasts | After the first sale 4 toasts stack and cover about 34% of the screen; the success toast also covers the next form's Save button | no cap on stacked toasts |

Advisory warnings (not counted as failures): Upload Logo / Remove / receipt close buttons are 32 px (target 44);
WhatsApp text starts "Hello Walk-in Customer" and does not list the items; "Customer" stays English on the French Reports page.

**What worked well (all pass):** cash sale in 5 actions with the receipt on screen in 16 ms (desktop CPU; re-measure on a phone), price auto-filled, change shown,
triple-tap records one sale; credit sale with deposit method and correct balance; payment with balance preview, no-method and
overpayment guarded; offline cash/credit/expense; backup export and restore on a clean install; corrupt file rejected;
cashier cannot reach Settings or Backup even by code; empty states on every list.
