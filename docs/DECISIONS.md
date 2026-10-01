# Bizora — product decision log

Decisions taken by the product owner (Ngwe). Do not reopen them unless asked.

| Date | Decision | Applies to |
|---|---|---|
| 2026-10-01 | **Sale reversal keeps its current behaviour**: it deletes the sale and resets the linked records (stock restored, payments and debt removed). No separate reversal/refund record type for now. Editing a completed cash sale is not planned; reverse it and record a new sale | Sales History reversal, `reversePosSale`, `delSale`, `cancelSale` |
| 2026-10-01 | **Deposits require an explicit payment method** (no default): Cash, Mobile Money, Bank Transfer, Card, Other; no Cheque for deposits | POS credit deposit, invoice deposit (4.3.8) |
| 2026-10-01 | **Old records with missing or unknown payment methods are never rewritten or guessed.** They are shown as "Not recorded" and left out of Expected Cash | 4.3.8 |
| 2026-10-01 | **Invoice deposit keeps the invoice date** (no change in 4.3.8; open for a future decision) | `saveSale` |
| 2026-10-01 | **Claude Code builds; the PM (Claude, project chat) writes briefs and audits; Ngwe approves, tests on Android and merges.** Nothing reaches `main` without Ngwe | All work |
