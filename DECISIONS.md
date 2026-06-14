
# DECISIONS.md — Decision Log

Each entry documents a significant engineering or product decision made during this project, with options considered and reasons for the final choice.

---

## Decision 1: Tech Stack — Django + React

**Options considered:**
- Node.js + Express + React
- Django + Django REST Framework + React
- Next.js (full-stack, single repo)

**Decision:** Django REST Framework + React

**Reason:** Django's ORM is better suited for complex relational queries needed for balance calculation (aggregating across expenses, splits, and settlements). DRF provides clean serialization, authentication, and validation. React gives a responsive single-page app without full-page reloads. Next.js was rejected because it would mix concerns and complicate the DB access layer.

---

## Decision 2: Custom User Model — Email as Login

**Options considered:**
- Use Django's default User model (username-based login)
- Extend with AbstractUser, keeping username
- Extend with AbstractUser, making email the login field

**Decision:** `AbstractUser` with `USERNAME_FIELD = 'email'`

**Reason:** Email-based login is the standard for modern apps (Splitwise uses it). Django requires this to be set before the first migration — it cannot be changed without resetting the database. Using AbstractUser preserves all built-in Django auth functionality (password hashing, sessions, permissions).

---

## Decision 3: Time-Based Group Membership (Separate Table)

**Options considered:**
- Simple many-to-many between User and Group
- Separate `GroupMembership` table with `joined_at` and `left_at` date fields

**Decision:** Separate `GroupMembership` table with full date tracking

**Reason:** The problem explicitly requires handling Meera leaving end of March and Sam joining mid-April. A simple M2M has no date fields — you cannot determine "was this person a member on this specific date?" The `GroupMembership` table with `joined_at`, `left_at`, and `is_active` answers: "At the time of this expense (date X), was person Y a member?" This is the core of Sam's and Meera's requirements.

**Trade-off:** Slightly more complex queries, but correctness is non-negotiable here.

---

## Decision 4: Currency Handling — Fixed Rate, Store Both Values

**Options considered:**
- Reject all USD entries as errors
- Use a live exchange rate API (e.g. Fixer.io)
- Use a fixed historical exchange rate

**Decision:** Fixed rate of ₹83.5 per USD; store both `amount` (original) and `amount_inr` (converted)

**Reason:** The CSV contains historical expenses from February–April 2026. Using a live rate now would give wrong results for past transactions — the rate changes daily. A fixed rate makes the import deterministic and auditable. Storing both the original USD amount and the converted INR amount ensures no information is lost. Rate of ₹83.5 is a reasonable approximate for early 2026.

**This directly addresses Priya's complaint:** "The sheet pretends a dollar is a rupee. That can't be right." The importer logs a `USD_CONVERSION` anomaly for every USD row so the conversion is visible.

---

## Decision 5: Balance Calculation Algorithm — On-the-Fly

**Options considered:**
- Calculate balances on the fly from the expenses and settlements tables on each request
- Cache balances in a separate `Balance` table, update on each expense write
- Use a PostgreSQL materialized view

**Decision:** Calculate on the fly per request

**Reason:** For a group of 5–6 people with ~50 expenses, the calculation is fast (< 100ms). On-the-fly is always accurate — no cache invalidation bugs when expenses are edited or deleted. Caching would add consistency complexity for marginal performance gain. At larger scale (thousands of members, millions of expenses), a caching layer would be added.

**Balance formula:**
```
For each expense:
  paid_by gets  +amount_inr
  each split member gets  -their split amount_owed

For each settlement:
  paid_by gets  +amount
  paid_to gets  -amount

Final balance = sum of all above per person
```

---

## Decision 6: Settlement Suggestions — Greedy Minimum Transactions

**Options considered:**
- Show all pairwise debts (O(n²) transactions)
- Minimize number of transactions using greedy algorithm

**Decision:** Greedy minimization algorithm (sort creditors and debtors by amount, match largest to largest)

**Reason:** Aisha's exact requirement: "one number per person, who pays whom, done." Pairwise debts in a 6-person group could mean 15 separate transactions. Greedy minimization collapses this to at most n-1 transactions. The algorithm: sort positive balances (creditors) and negative balances (debtors) by magnitude; repeatedly match the largest debtor with the largest creditor until all are settled.

**Trade-off:** The minimum-transaction solution is not unique — the greedy approach gives *a* valid minimum-transaction solution, not necessarily the most "convenient" one (e.g., it doesn't try to keep transactions within friend pairs). For 6 people this is fine.

---

## Decision 7: Negative Amounts = Refunds (Not Errors)

**Options considered:**
- Treat negative amount as error, skip row
- Treat as refund (keep as negative expense)
- Ask user to decide via approval workflow

**Decision:** Treat as refund automatically, take absolute value, log it

**Reason:** The CSV contains a "Parasailing refund" row with `-30 USD`. The description makes intent unambiguous — this is a real refund that reduces costs. Treating it as an error would silently lose a financial record. Taking the absolute value and noting it as a refund in the import report is the correct interpretation. If there were ambiguous negative amounts without explanatory descriptions, the approval workflow would be triggered instead.

---

## Decision 8: Duplicate Detection — Two Levels

**Options considered:**
- Exact match only (same date + description + amount)
- Fuzzy match (same date + similar description, different amount or payer)
- No duplicate detection

**Decision:** Both exact and fuzzy matching, with different actions for each

**Reason:** The CSV has two distinct kinds of duplicates:
1. **Exact duplicates** (e.g. Rows 4 & 5): same date, same description, same amount. One is clearly an accidental double-entry. Auto-skip the second.
2. **Conflict duplicates** (e.g. Rows 23 & 24): same dinner, different amounts/payers. Could be two people logging the same event, or two real events. Requires human judgement → flag as `requires_approval`, skip both, surface in import report.

**Duplicate key:** `(date, description.lower().strip(), str(amount))` for exact; `(date, description[:15].lower())` for fuzzy.

---

## Decision 9: Missing Payer → Skip, Don't Guess

**Options considered:**
- Default to the importing user
- Default to the group creator
- Skip the row and require manual entry

**Decision:** Skip row, log as `MISSING_PAYER`, show in import report

**Reason:** The payer determines who gets credit in the balance calculation. Guessing incorrectly would silently introduce wrong financial data — which is worse than missing data. The import report clearly shows which rows were skipped and why, allowing the user to add them manually with correct information.

---

## Decision 10: Settlements Disguised as Expenses → Reclassify

**Options considered:**
- Import as regular expenses (wrong — double-counts money)
- Skip them entirely (loses the financial record)
- Reclassify as `Settlement` objects

**Decision:** Detect by keyword scanning and reclassify as `Settlement`

**Reason:** Importing "Rohan paid Aisha back ₹5,000" as an expense would add ₹5,000 to Rohan's costs and split it among members — completely wrong. It's a debt repayment that should reduce Rohan's debt to Aisha. Settlement keywords checked: `["settlement", "paid back", "paid aisha back", "deposit share"]`. When detected, we extract payer and payee, create a `Settlement` record, and skip creating an `Expense`.

---

## Decision 11: Soft Delete for Expenses

**Options considered:**
- Hard delete (`DELETE FROM` database)
- Soft delete (`is_deleted = True` flag, filter from queries)

**Decision:** Soft delete with `is_deleted` flag

**Reason:** Meera's requirement: "I want to approve anything the app deletes or changes." Soft delete preserves the data row while hiding it from normal views. It also maintains referential integrity (splits still exist for audit purposes) and allows an approval workflow where Meera can see what's been "deleted" and restore if needed. Hard delete would permanently destroy records that might be needed for dispute resolution.

---

## Decision 12: PostgreSQL over SQLite

**Options considered:**
- SQLite (no setup, file-based, simpler)
- PostgreSQL (production-grade, hosted on Railway)

**Decision:** PostgreSQL

**Reason:** The assignment requires relational DBs in a production-grade setup. PostgreSQL supports JSONField natively (used for storing the full import report), handles concurrent writes better, and is what Railway provides as a managed service. SQLite would work locally but cannot be used on Railway without custom configuration. The `dj-database-url` library makes switching trivial — local `.env` can use local PG, Railway auto-injects `DATABASE_URL`.

---

## Decision 13: Importer Anomaly Handling — "Detect, Surface, Handle" Policy

**Options considered:**
- Crash on first error (strict mode)
- Silently guess and continue (lenient mode)
- Classify each anomaly, apply per-type policy, always report

**Decision:** Per-type policy with mandatory reporting to user

**Reason:** A crashed import loses all data. A silent guess creates wrong data. The correct answer is to classify every anomaly, apply a documented policy (auto-fix, skip, or require-approval), and always show the user a full report. The three action types used:
- `auto_fixed` — safe correction (strip comma, normalize case, default currency)
- `skipped` — cannot safely fix (missing payer, zero amount, bad percentage sum)
- `requires_approval` — ambiguous situation (fuzzy duplicate, conflicting amounts)

This directly satisfies Meera's requirement: "I want to approve anything the app deletes or changes."

---

## Decision 14: Balance Scope — Full Group History vs Active Members Only

**Options considered:**
- Only show balances for currently active members
- Show balances for all members who ever participated (including Meera, Dev)

**Decision:** Show balances for all members who appear in expenses (including former members)

**Reason:** Meera left, but she still owes or is owed money from February/March expenses. Dev participated in trip expenses. Hiding former members from the balance view would make the group balance not sum to zero and lose real financial obligations. The balance view includes everyone who has `ExpenseSplit` rows, regardless of current membership status.