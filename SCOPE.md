
# SCOPE.md — Anomaly Log & Database Schema

## Database Schema

### users_user
| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | Primary key |
| email | EmailField | Unique, used as login identifier |
| username | CharField | Display name (used in splits/balances) |
| password | CharField | Hashed via Django auth |
| phone | CharField | Optional |
| created_at | DateTimeField | Auto |

> Extends `AbstractUser` with `EMAIL_FIELD = 'email'` and `USERNAME_FIELD = 'email'`. This was decided before first migration — cannot be changed without a DB reset.

### groups_group
| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | Primary key |
| name | CharField | Group name |
| description | TextField | Optional |
| created_by | FK → User | Who created the group |
| created_at | DateTimeField | Auto |
| updated_at | DateTimeField | Auto |

### groups_groupmembership
| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | Primary key |
| group | FK → Group | |
| user | FK → User | |
| joined_at | DateField | Date member joined |
| left_at | DateField | Null if still active |
| is_active | BooleanField | Current member? |

This table handles Meera leaving end of March and Sam joining mid-April. The importer queries this table to decide whether a person should be in a split for a given expense date.

### expenses_expense
| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | Primary key |
| group | FK → Group | |
| description | CharField(500) | |
| amount | DecimalField(12,2) | Original amount in original currency |
| currency | CharField(3) | INR or USD |
| amount_inr | DecimalField(12,2) | Converted to INR (=amount if INR) |
| paid_by | FK → User | Person who paid upfront |
| date | DateField | Expense date |
| split_type | CharField | equal / unequal / percentage / share |
| notes | TextField | Optional |
| is_deleted | BooleanField | Soft delete flag (default False) |
| import_row | IntegerField | Source CSV row number (null if manually added) |
| created_at | DateTimeField | Auto |
| updated_at | DateTimeField | Auto |

> `is_deleted` enables soft delete: data is preserved, audit trail maintained. Satisfies Meera's requirement: "I want to approve anything the app deletes."

### expenses_expensesplit
| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | Primary key |
| expense | FK → Expense | |
| user | FK → User | |
| amount_owed | DecimalField(12,2) | How much this person owes in INR |
| percentage | DecimalField(5,2) | Null unless percentage split |
| shares | IntegerField | Null unless share split |

> One row per person per expense. Balance calculation iterates these rows.

### expenses_settlement
| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | Primary key |
| group | FK → Group | |
| paid_by | FK → User | Who paid |
| paid_to | FK → User | Who received |
| amount | DecimalField(12,2) | Amount paid |
| currency | CharField(3) | Currency |
| date | DateField | Payment date |
| notes | TextField | Optional |
| created_at | DateTimeField | Auto |

### importer_importsession
| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | Primary key |
| filename | CharField | Original CSV filename |
| imported_by | FK → User | |
| imported_at | DateTimeField | Auto |
| status | CharField | pending / completed / failed |
| total_rows | IntegerField | |
| imported_rows | IntegerField | |
| skipped_rows | IntegerField | |
| report | JSONField | Full anomaly report stored as JSON |

### importer_importanomaly
| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | Primary key |
| session | FK → ImportSession | |
| row_number | IntegerField | CSV row number (1-indexed from header=1) |
| raw_data | JSONField | Original row as dict |
| anomaly_type | CharField | Type code (see list below) |
| description | TextField | Human-readable explanation |
| action_taken | CharField | auto_fixed / skipped / requires_approval |
| resolution | TextField | What the importer did |
| requires_approval | BooleanField | Needs human review |
| approved_by | FK → User | Null until approved |
| approved_at | DateTimeField | Null until approved |

---

## Anomaly Log — expenses_export.csv

All row numbers below refer to CSV row numbers (header = row 1, data starts at row 2).

---

### Anomaly 1 — DUPLICATE (Rows 4 & 5)
- **Problem:** Two rows for "Dinner at Marina Bites" on same date (08-02-2026), same amount ₹3200, same payer (Dev). One is clearly a double-entry.
- **Detection:** Exact match on `(date, description.lower(), amount)` tuple.
- **Policy:** Keep first occurrence (Row 4, which has notes). Flag Row 5 as `DUPLICATE`, skip it. User informed via import report.
- **Type code:** `DUPLICATE`

---

### Anomaly 2 — AMOUNT_FORMAT (Row 6)
- **Problem:** Amount field contains `"1,200"` — a comma-formatted number, not a valid decimal.
- **Detection:** `Decimal("1,200")` raises `InvalidOperation`. Importer strips commas and retries.
- **Policy:** Strip commas, parse as `1200`. Auto-fixed. Logged.
- **Type code:** `AMOUNT_FORMAT` (handled in `parse_amount()`)

---

### Anomaly 3 — NAME_CASE (Row 8)
- **Problem:** `paid_by = "priya"` (all lowercase). Canonical name is `"Priya"`.
- **Detection:** `normalize_name()` does case-insensitive exact match against known members list.
- **Policy:** Normalize to canonical form. Auto-fixed.
- **Type code:** `NAME_CASE`

---

### Anomaly 4 — PRECISION (Row 9)
- **Problem:** Amount = `899.995` — three decimal places. INR uses max 2 decimal places.
- **Detection:** After parsing, `amount.quantize(Decimal('0.01'))` differs from original.
- **Policy:** Round to `₹900.00` using `ROUND_HALF_UP`. Auto-fixed. Logged.
- **Type code:** `PRECISION`

---

### Anomaly 5 — NAME_CASE / FUZZY_MATCH (Row 10)
- **Problem:** `paid_by = "Priya S"` — not an exact match. Fuzzy matched to "Priya".
- **Detection:** `normalize_name()` fails. `fuzzy_match_name()` checks if known name is substring of input or vice versa.
- **Policy:** If confident match found, auto-fix with log. If ambiguous, skip.
- **Type code:** `NAME_CASE`

---

### Anomaly 6 — MISSING_PAYER (Row 12)
- **Problem:** `paid_by` field is blank.
- **Detection:** After normalization and fuzzy match, `paid_by_name` is still `None`.
- **Policy:** Cannot determine payer. Skip row, log as `MISSING_PAYER`. User must add manually.
- **Type code:** `MISSING_PAYER`

---

### Anomaly 7 — SETTLEMENT_AS_EXPENSE (Row 13)
- **Problem:** Description `"Rohan paid Aisha back"` with notes `"this is a settlement not an expense??"`. This is a debt repayment, not a shared expense.
- **Detection:** Keyword scan of description and notes: `["settlement", "paid back", "paid aisha back", "deposit share"]`.
- **Policy:** Reclassify as `Settlement` object (not `Expense`). Both payer and payee extracted from the row. Logged.
- **Type code:** `SETTLEMENT_AS_EXPENSE`

---

### Anomaly 8 — PERCENT_SUM_INVALID (Row 14)
- **Problem:** Pizza Friday: Aisha 30% + Rohan 30% + Priya 30% + Meera 20% = **110%**. Must sum to exactly 100%.
- **Detection:** Sum all percentages from `split_details`. If `|sum - 100| > 0.01`, reject.
- **Policy:** Row is skipped. Cannot guess how to redistribute. User must correct and re-import or enter manually.
- **Type code:** `PERCENT_SUM_INVALID`

---

### Anomaly 9 — UNKNOWN_MEMBER (Row 22)
- **Problem:** `split_with` includes `"Dev's friend Kabir"` — not a registered member.
- **Detection:** `normalize_name()` and `fuzzy_match_name()` both return `None`.
- **Policy:** Exclude unrecognized member from split. Continue with known members only. Logged.
- **Type code:** `UNKNOWN_MEMBER`

---

### Anomaly 10 — DUPLICATE_CONFLICT (Rows 23 & 24)
- **Problem:** Two rows for same dinner at "Thalassa" on 11-03-2026 but different amounts (₹2400 vs ₹2450) and different payers (Aisha vs Rohan). This could be two people logging the same shared dinner, or two separate events.
- **Detection:** Fuzzy duplicate: same date + first 15 chars of description match.
- **Policy:** Flag both as `requires_approval`. Skip both for now. Human must decide which is correct (or if both are valid).
- **Type code:** `FUZZY_DUPLICATE`

---

### Anomaly 11 — NEGATIVE_AMOUNT (Row 25)
- **Problem:** Parasailing refund with amount `-30 USD`. Negative expense.
- **Detection:** After `parse_amount()`, value `< 0`.
- **Policy:** Treat as refund. Take absolute value, note it's a refund. Create as normal expense with `abs(amount)`. Logged as `NEGATIVE_AMOUNT`.
- **Type code:** `NEGATIVE_AMOUNT`

---

### Anomaly 12 — DATE_FORMAT (Row 26)
- **Problem:** Date is `"Mar-14"` — non-standard format. Also `paid_by = "rohan "` has trailing whitespace.
- **Detection:** All standard date formats tried. `"%b-%d"` format matches but gives year 1900 — importer auto-corrects to current year (2026).
- **Policy:** Parse `"Mar-14"` as `14-03-2026`. Strip whitespace from all name fields. Both auto-fixed.
- **Type code:** `DATE_FORMAT`

---

### Anomaly 13 — MISSING_CURRENCY (Row 27)
- **Problem:** `currency` field is blank.
- **Detection:** `currency.strip()` is empty string.
- **Policy:** Default to INR (all flatmates are India-based, INR is the group default). Log assumption.
- **Type code:** `MISSING_CURRENCY`

---

### Anomaly 14 — ZERO_AMOUNT (Row 30)
- **Problem:** Amount is `0`. Notes say `"counted twice earlier - fixing later"`.
- **Detection:** After parsing, `amount == 0`.
- **Policy:** Skip row entirely. Zero amounts have no financial effect and the note confirms this is a placeholder.
- **Type code:** `ZERO_AMOUNT`

---

### Anomaly 15 — AMBIGUOUS_DATE (Row 33)
- **Problem:** Date `"04-05-2026"` is ambiguous — could be April 5 (MM-DD-YYYY) or May 4 (DD-MM-YYYY).
- **Detection:** Both interpretations are valid dates. Importer tries `DD-MM-YYYY` first (our standard format).
- **Policy:** Parse as **DD-MM-YYYY** → May 4, 2026. Log the ambiguity so user is aware.
- **Type code:** `AMBIGUOUS_DATE` (logged as info, not a block)

---

### Anomaly 16 — MEMBER_AFTER_LEAVING (Row 35)
- **Problem:** Meera listed in `split_with` for an April 2026 expense. Meera moved out end of March 2026 (left_at = 31-03-2026).
- **Detection:** For each member in `split_with`, check `parsed_date > MEERA_LEFT (2026-03-31)`.
- **Policy:** Remove Meera from split. Redistribute among remaining active members. Log it.
- **Type code:** `MEMBER_AFTER_LEAVING`

---

### Anomaly 17 — SETTLEMENT_AS_EXPENSE (Row 37)
- **Problem:** `"Sam deposit share"` — Sam paying Aisha ₹15,000 as deposit contribution. This is a transfer/settlement, not a shared living expense.
- **Detection:** `"deposit share"` matches settlement keyword list.
- **Policy:** Reclassify as `Settlement`. Logged.
- **Type code:** `SETTLEMENT_AS_EXPENSE`

---

### Anomaly 18 — SPLIT_TYPE_CONFLICT (Row 41)
- **Problem:** `split_type = "equal"` but `split_details` has share values `{Aisha:1, Rohan:1, Priya:1, Sam:1}`. Conflict between declared type and provided details.
- **Detection:** split_type is `equal` but split_details is non-empty.
- **Policy:** Since all shares are equal (1 each), outcome is mathematically identical. Treat as equal split. Log the conflict.
- **Type code:** `SPLIT_TYPE_CONFLICT`

---

### Anomaly 19 — USD_CONVERSION (Multiple rows: trip expenses)
- **Problem:** Trip expenses logged in USD. The original spreadsheet stored them as-is, treating `$1 = ₹1` — clearly wrong.
- **Detection:** `currency == 'USD'`.
- **Policy:** Convert all USD amounts to INR at rate **₹83.5 per USD**. Store original USD amount in `amount`, converted INR amount in `amount_inr`. All balance calculations use `amount_inr`. Logged per row.
- **Type code:** `USD_CONVERSION`

---

### Anomaly 20 — MEMBER_BEFORE_JOINING (Sam in pre-April rows)
- **Problem:** Sam joined mid-April (15-04-2026). Any expense before that date should not include Sam in the split.
- **Detection:** For each member in `split_with`, check `parsed_date < SAM_JOINED (2026-04-15)` where member is Sam.
- **Policy:** Exclude Sam from splits on expenses dated before 15-04-2026. Log each occurrence.
- **Type code:** `MEMBER_BEFORE_JOINING`