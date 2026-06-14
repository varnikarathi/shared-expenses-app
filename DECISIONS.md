 
# DECISIONS.md — Decision Log

## Decision 1: Tech Stack — Django + React

**Options considered:**
- Node.js + Express + React
- Django + React
- Next.js (full-stack)

**Decision:** Django + React

**Reason:** The Spreetail JD explicitly mentions Python and Django as required skills. Django ORM is also better suited for complex relational queries needed for balance calculations. DRF (Django REST Framework) provides a clean API layer with built-in serialization, authentication, and validation.

---

## Decision 2: Custom User Model

**Options considered:**
- Use Django's default User model
- Extend with AbstractUser

**Decision:** AbstractUser with email as USERNAME_FIELD

**Reason:** Splitwise uses email-based login, not username. Using AbstractUser lets us keep all of Django's built-in auth functionality while making email the primary login field. Must be done before first migration — cannot be changed later without resetting the database.

---

## Decision 3: Time-Based Group Membership

**Options considered:**
- Simple many-to-many between User and Group
- Separate GroupMembership table with joined_at and left_at dates

**Decision:** Separate GroupMembership table with date fields

**Reason:** The problem explicitly requires handling Meera leaving end of March and Sam joining mid-April. A simple M2M cannot track when someone joined or left. The GroupMembership table with `joined_at`, `left_at`, and `is_active` fields allows us to check membership status at any point in time — critical for correct expense splitting.

---

## Decision 4: Currency Handling

**Options considered:**
- Reject all USD entries as errors
- Use live exchange rate API
- Use fixed exchange rate

**Decision:** Fixed rate of ₹83.5 per USD, store both original and converted amounts

**Reason:** The CSV contains historical expenses from February-April 2026. Using a live rate would give wrong results for past transactions. A fixed rate makes the conversion deterministic and auditable. We store `amount` (original) and `amount_inr` (converted) so the original data is never lost. Rate of 83.5 is a reasonable average for early 2026.

---

## Decision 5: Balance Calculation Algorithm

**Options considered:**
- Calculate on the fly from expenses table
- Cache balances in a separate table
- Use a materialized view

**Decision:** Calculate on the fly

**Reason:** For a small group (5-6 people), on-the-fly calculation is fast enough and always accurate. Caching introduces consistency problems — if an expense is edited or deleted, the cache must be invalidated. For scale, caching would be added later.

**Formula:**
- For each expense: `paid_by` gets +amount, each split member gets -their_split
- For each settlement: `paid_by` gets +amount, `paid_to` gets -amount
- Final balance = sum of all above

---

## Decision 6: Settlement Suggestions (Minimum Transactions)

**Options considered:**
- Show all pairwise debts
- Minimize number of transactions (greedy algorithm)

**Decision:** Greedy minimization algorithm

**Reason:** Aisha's requirement — "one number per person, who pays whom, done." The greedy algorithm sorts creditors and debtors by amount, then matches the largest creditor with the largest debtor repeatedly. This minimizes the number of transactions needed to settle all debts.

---

## Decision 7: Negative Amounts = Refunds

**Options considered:**
- Treat as error, skip row
- Treat as refund (negative expense)
- Ask user to decide

**Decision:** Treat as refund automatically, log it

**Reason:** The CSV contains a "Parasailing refund" with -30 USD. This is clearly intentional. Treating it as an error would lose real financial data. We convert to positive amount and note it as a refund in the description.

---

## Decision 8: Duplicate Detection Strategy

**Options considered:**
- Exact match only (same date + description + amount)
- Fuzzy match (same date + similar description)
- No duplicate detection

**Decision:** Both exact and fuzzy matching, different actions for each

**Reason:** The CSV has two types of duplicates:
1. Exact duplicates (Row 4 & 5) — same everything, clearly one should be deleted
2. Conflict duplicates (Row 23 & 24) — same dinner, different amounts/payers — human decision needed

Exact duplicates: skip the second occurrence automatically.
Conflict duplicates: flag both as `requires_approval`, skip both.

---

## Decision 9: Missing Payer = Skip Row

**Options considered:**
- Default to current user
- Default to group creator
- Skip row and require manual entry

**Decision:** Skip row, log it as requiring manual entry

**Reason:** Guessing the payer would introduce incorrect financial data. It's better to skip the row and let the user add it manually with correct information. The import report clearly shows which rows were skipped and why.

---

## Decision 10: Settlements Disguised as Expenses

**Options considered:**
- Import as regular expenses
- Skip them
- Reclassify as settlements

**Decision:** Reclassify as settlements

**Reason:** Importing "Rohan paid Aisha back ₹5000" as an expense would double-count the money. It's actually a debt repayment that should reduce balances, not create new ones. We detect settlement keywords in description and notes, then create a Settlement object instead of an Expense.

---

## Decision 11: Soft Delete for Expenses

**Options considered:**
- Hard delete (DELETE FROM db)
- Soft delete (is_deleted flag)

**Decision:** Soft delete with is_deleted flag

**Reason:** Meera's requirement — "I want to approve anything the app deletes or changes." Soft delete preserves the data while hiding it from normal views. It also maintains referential integrity and allows audit trails.

---

## Decision 12: PostgreSQL over SQLite

**Options considered:**
- SQLite (simpler, no setup)
- PostgreSQL

**Decision:** PostgreSQL

**Reason:** The assignment explicitly requires relational DBs in a production-grade setup. PostgreSQL handles concurrent writes better, supports JSONField natively (used for import reports), and is what Spreetail would use in production.