 
# SCOPE.md — Anomaly Log & Database Schema

## Database Schema

### users_user
| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | Primary key |
| email | EmailField | Unique, used as login |
| username | CharField | Display name |
| password | CharField | Hashed |
| phone | CharField | Optional |
| created_at | DateTimeField | Auto |

### groups_group
| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | Primary key |
| name | CharField | Group name |
| description | TextField | Optional |
| created_by | FK → User | Who created it |
| created_at | DateTimeField | Auto |

### groups_groupmembership
| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | Primary key |
| group | FK → Group | |
| user | FK → User | |
| joined_at | DateField | When they joined |
| left_at | DateField | Null if still active |
| is_active | BooleanField | Current member? |

This table handles Meera leaving end of March and Sam joining mid-April.

### expenses_expense
| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | Primary key |
| group | FK → Group | |
| description | CharField | |
| amount | DecimalField | Original amount |
| currency | CharField | INR or USD |
| amount_inr | DecimalField | Converted to INR |
| paid_by | FK → User | |
| date | DateField | |
| split_type | CharField | equal/unequal/percentage/share |
| notes | TextField | Optional |
| is_deleted | BooleanField | Soft delete |
| import_row | IntegerField | Source CSV row number |

### expenses_expensesplit
| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | Primary key |
| expense | FK → Expense | |
| user | FK → User | |
| amount_owed | DecimalField | How much this person owes |
| percentage | DecimalField | For percentage splits |
| shares | IntegerField | For share splits |

### expenses_settlement
| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | Primary key |
| group | FK → Group | |
| paid_by | FK → User | Who paid |
| paid_to | FK → User | Who received |
| amount | DecimalField | |
| currency | CharField | |
| date | DateField | |
| notes | TextField | Optional |

### importer_importsession
| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | Primary key |
| filename | CharField | |
| imported_by | FK → User | |
| imported_at | DateTimeField | Auto |
| status | CharField | pending/completed/failed |
| total_rows | IntegerField | |
| imported_rows | IntegerField | |
| skipped_rows | IntegerField | |
| report | JSONField | Full report stored |

### importer_importanomaly
| Column | Type | Notes |
|--------|------|-------|
| id | BigAutoField | Primary key |
| session | FK → ImportSession | |
| row_number | IntegerField | CSV row number |
| raw_data | JSONField | Original row data |
| anomaly_type | CharField | Type of problem |
| description | TextField | Human-readable explanation |
| action_taken | CharField | auto_fixed/skipped/requires_approval |
| resolution | TextField | What was done |
| requires_approval | BooleanField | Needs human review |
| approved_by | FK → User | Null until approved |
| approved_at | DateTimeField | Null until approved |

---

## Anomaly Log — expenses_export.csv

### Anomaly 1 — DUPLICATE (Rows 4 & 5)
- **Problem:** Two rows for "Dinner at Marina Bites" on same date (08-02-2026), same amount ₹3200, same payer Dev.
- **Policy:** Keep first occurrence (Row 4, which has notes). Flag Row 5 as duplicate and skip it.

### Anomaly 2 — AMOUNT_FORMAT (Row 6)
- **Problem:** Amount is "1,200" — comma inside number is not a valid decimal.
- **Policy:** Strip commas automatically, parse as 1200. Log as auto-fixed.

### Anomaly 3 — NAME_CASE (Row 8)
- **Problem:** paid_by = "priya" (lowercase). Canonical name is "Priya".
- **Policy:** Case-insensitive normalization. Auto-fixed.

### Anomaly 4 — PRECISION (Row 9)
- **Problem:** Amount = 899.995 — three decimal places. INR uses max 2.
- **Policy:** Round to ₹900.00 using ROUND_HALF_UP. Auto-fixed.

### Anomaly 5 — UNKNOWN_PAYER (Row 10)
- **Problem:** paid_by = "Priya S" — not an exact match. Fuzzy matched to "Priya".
- **Policy:** Fuzzy name matching. If confident match found, auto-fix with log.

### Anomaly 6 — MISSING_PAYER (Row 12)
- **Problem:** paid_by is blank.
- **Policy:** Cannot determine payer. Skip row and log it.

### Anomaly 7 — SETTLEMENT_AS_EXPENSE (Row 13)
- **Problem:** Description "Rohan paid Aisha back" with notes "this is a settlement not an expense??" — this is a settlement, not an expense.
- **Policy:** Detect settlement keywords. Reclassify as Settlement object, not Expense.

### Anomaly 8 — PERCENT_SUM_INVALID (Row 14)
- **Problem:** Pizza Friday percentages: Aisha 30 + Rohan 30 + Priya 30 + Meera 20 = 110%. Does not sum to 100%.
- **Policy:** Block import of this row. Require correction.

### Anomaly 9 — UNKNOWN_MEMBER (Row 22)
- **Problem:** split_with includes "Dev's friend Kabir" — not a registered member.
- **Policy:** Exclude unknown member from split, log it. Continue with known members only.

### Anomaly 10 — DUPLICATE_CONFLICT (Rows 23 & 24)
- **Problem:** Two rows for same dinner at Thalassa on 11-03-2026 but different amounts (₹2400 vs ₹2450) and different payers (Aisha vs Rohan).
- **Policy:** Flag both as conflicting duplicates. Require user approval. Skip both for now.

### Anomaly 11 — NEGATIVE_AMOUNT (Row 25)
- **Problem:** Parasailing refund with amount -30 USD.
- **Policy:** Treat as refund. Convert to positive, create expense with notes indicating it's a refund.

### Anomaly 12 — DATE_FORMAT (Row 26)
- **Problem:** Date is "Mar-14" — non-standard format. Also paid_by = "rohan " has trailing space.
- **Policy:** Parse "Mar-14" as 14-03-2026. Strip whitespace from names. Both auto-fixed.

### Anomaly 13 — MISSING_CURRENCY (Row 27)
- **Problem:** Currency field is blank.
- **Policy:** Default to INR (all flatmates are India-based). Log assumption.

### Anomaly 14 — ZERO_AMOUNT (Row 30)
- **Problem:** Amount is 0. Notes say "counted twice earlier - fixing later".
- **Policy:** Skip row entirely. Zero amounts have no financial effect.

### Anomaly 15 — AMBIGUOUS_DATE (Row 33)
- **Problem:** Date "04-05-2026" could be April 5 or May 4 depending on format.
- **Policy:** Parse as DD-MM-YYYY (May 4, 2026) as per our standard format. Log ambiguity.

### Anomaly 16 — MEMBER_AFTER_LEAVING (Row 35)
- **Problem:** Meera listed in split_with for an April 2026 expense. Meera moved out end of March 2026.
- **Policy:** Remove Meera from split. Redistribute among active members. Log it.

### Anomaly 17 — SETTLEMENT_AS_EXPENSE (Row 37)
- **Problem:** "Sam deposit share" — Sam paying Aisha ₹15000 as deposit. This is a transfer, not a shared expense.
- **Policy:** Reclassify as settlement.

### Anomaly 18 — SPLIT_TYPE_CONFLICT (Row 41)
- **Problem:** split_type = "equal" but split_details has share values. All shares are 1 so result is mathematically same.
- **Policy:** Treat as equal split since outcome is identical. Log conflict.

### Anomaly 19 — USD_CONVERSION (Multiple rows)
- **Problem:** Trip expenses logged in USD. Original spreadsheet treated $1 = ₹1 (wrong).
- **Policy:** Convert all USD amounts to INR at rate 83.5. Store both original and converted amounts.

### Anomaly 20 — MEMBER_BEFORE_JOINING (Sam in pre-April rows)
- **Problem:** Sam joined mid-April. Any expense before that date should not include Sam.
- **Policy:** Exclude Sam from splits on expenses dated before 15-04-2026.