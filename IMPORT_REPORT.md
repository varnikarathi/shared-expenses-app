# Import Report & Anomaly Log

*The app detected 20 distinct types of anomalies in `expenses_export.csv`. Each was classified and handled according to a specific policy designed to maintain financial accuracy.*

---

**1. DUPLICATE (Rows 4 & 5)**
- **Problem:** Two rows for "Dinner at Marina Bites" on the same date with the same amount. One is clearly a double-entry.
- **Action Taken:** `requires_approval`. The first occurrence is kept, while the duplicate is flagged for human review via the UI's Approval Workflow.

**2. AMOUNT_FORMAT (Row 6)**
- **Problem:** Amount field contains `"1,200"` — a comma-formatted string, causing database parsing errors.
- **Action Taken:** `auto_fixed`. Commas are stripped and parsed cleanly as `1200`.

**3. NAME_CASE (Row 8)**
- **Problem:** Payer entered as `"priya"` (lowercase).
- **Action Taken:** `auto_fixed`. Normalized to the canonical user format `"Priya"`.

**4. PRECISION (Row 9)**
- **Problem:** Amount entered as `899.995` (three decimal places). INR standard is max 2.
- **Action Taken:** `auto_fixed`. Automatically rounded to `900.00` using `ROUND_HALF_UP`.

**5. FUZZY_MATCH (Row 10)**
- **Problem:** Payer entered as `"Priya S"` which doesn't exactly match the database.
- **Action Taken:** `auto_fixed`. Fuzzy matched to the registered user "Priya".

**6. MISSING_PAYER (Row 12)**
- **Problem:** `paid_by` field is completely blank. 
- **Action Taken:** `skipped`. Skipping row entirely because missing payer corrupts balance math. User is informed via the UI log.

**7. SETTLEMENT_AS_EXPENSE (Row 13)**
- **Problem:** "Rohan paid Aisha back" — This is a debt repayment, not a shared group expense.
- **Action Taken:** `auto_fixed`. Keyword scanner reclassifies this from an `Expense` object into a `Settlement` object to prevent double-charging.

**8. PERCENT_SUM_INVALID (Row 14)**
- **Problem:** A percentage split where the shares sum to 110% instead of 100%.
- **Action Taken:** `skipped`. Cannot guess how to redistribute percentages. Row skipped and flagged for user correction.

**9. UNKNOWN_MEMBER (Row 22)**
- **Problem:** Split includes "Dev's friend Kabir", who is not registered in the app.
- **Action Taken:** `auto_fixed`. Unknown member is excluded from the split; the expense is divided among registered members.

**10. DUPLICATE_CONFLICT (Rows 23 & 24)**
- **Problem:** Two similar rows for a "Thalassa" dinner on the same date, but different amounts and payers.
- **Action Taken:** `requires_approval`. Both are flagged as fuzzy duplicates and skipped. User must approve/reject via the UI to resolve the conflict.

**11. NEGATIVE_AMOUNT (Row 25)**
- **Problem:** A refund logged as `-30 USD`.
- **Action Taken:** `auto_fixed`. Converted to a positive value but logged as a refund to offset group costs correctly.

**12. DATE_FORMAT (Row 26)**
- **Problem:** Date is `"Mar-14"` instead of the standard `DD-MM-YYYY`.
- **Action Taken:** `auto_fixed`. Parsed to standard format and assigned to the current year (`14-03-2026`).

**13. MISSING_CURRENCY (Row 27)**
- **Problem:** Currency column is blank.
- **Action Taken:** `auto_fixed`. Automatically defaults to `INR`.

**14. ZERO_AMOUNT (Row 30)**
- **Problem:** Amount is `0` (used as a placeholder note in the spreadsheet).
- **Action Taken:** `skipped`. Zero amounts have no financial effect; ignored.

**15. AMBIGUOUS_DATE (Row 33)**
- **Problem:** Date `"04-05-2026"` could be April 5th or May 4th.
- **Action Taken:** `auto_fixed`. System defaults to `DD-MM-YYYY` standard and assumes May 4th.

**16. MEMBER_AFTER_LEAVING (Row 35)**
- **Problem:** Meera is included in a split for an April expense, but she moved out on March 31st.
- **Action Taken:** `auto_fixed`. The app validates dates against the `GroupMembership` table and automatically removes Meera from the split, recalculating shares for active members.

**17. SETTLEMENT_AS_EXPENSE (Row 37)**
- **Problem:** "Sam deposit share" (paying Aisha for the deposit). 
- **Action Taken:** `auto_fixed`. Keyword scanner detects "deposit share" and correctly imports this as a `Settlement` rather than a shared expense.

**18. SPLIT_TYPE_CONFLICT (Row 41)**
- **Problem:** Row claims it is an "equal" split, but provides specific share ratios.
- **Action Taken:** `auto_fixed`. Since ratios are mathematically identical (1:1:1), it ignores the conflict and forces an equal split.

**19. USD_CONVERSION (Multiple Trip Rows)**
- **Problem:** The CSV treats `$1` the same as `₹1`, badly skewing balances (Priya's specific complaint).
- **Action Taken:** `auto_fixed`. Detects `USD` and dynamically creates an `amount_inr` field using a fixed conversion rate of ₹83.5, which the balance engine relies on.

**20. MEMBER_BEFORE_JOINING (Pre-April Rows)**
- **Problem:** Sam joined mid-April, but is accidentally included in splits from February.
- **Action Taken:** `auto_fixed`. The system cross-references his `GroupMembership` join date and removes his financial liability for any dates prior to his move-in.
