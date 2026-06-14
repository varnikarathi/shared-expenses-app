# AI_USAGE.md — AI Collaboration Log

## AI Tools Used

| Tool | Used For |
|------|----------|
| **Antigravity (Google DeepMind)** | Primary development collaborator in this session — architecture, debugging, implementing balance breakdown, anomaly approval workflow, documentation |
| **Claude (Anthropic) — claude.ai** | Earlier sessions — initial project scaffolding, models, views, CSV anomaly detection logic |

All AI output was reviewed, understood, and in multiple cases corrected before use. The engineer is responsible for every line submitted.

---

## How AI Was Used

AI tools were used to:
- Plan the project architecture and database schema
- Generate boilerplate Django models, serializers, views, and URL configs
- Generate React page components and styling
- Design the CSV anomaly detection and classification logic
- Implement the balance breakdown endpoint (Rohan's requirement)
- Implement the anomaly approval/rejection workflow (Meera's requirement)
- Write and update documentation (README, SCOPE, DECISIONS)

Every piece of generated code was read line by line, tested locally, and corrected where necessary.

---

## Key Prompts Used

### Prompt 1 — Project Planning
> "I need to build a Splitwise clone with Django + React + PostgreSQL. The app needs login, groups with time-based membership (one member left, one joined mid-month), expenses with 4 split types, CSV import with anomaly detection, and balance calculation. Give me the complete database schema first."

### Prompt 2 — CSV Anomaly Detection
> "Here is the expenses_export.csv. Analyze every row and identify all data problems. For each problem tell me: what it is, which row, and what the policy should be to handle it."

### Prompt 3 — Balance Engine
> "Write a Django view that calculates group balances. For each expense, the payer gets +amount and each split member gets -their_split. Then apply settlements. Then use a greedy algorithm to suggest minimum transactions to settle all debts."

### Prompt 4 — Importer Logic
> "Write a Django view that imports a CSV file and detects these anomalies: duplicates, settlements disguised as expenses, missing payer, invalid amounts with commas, USD currency without conversion, negative amounts, dates after a member left, dates before a member joined, percentages not summing to 100."

### Prompt 5 — Balance Breakdown (Rohan's requirement)
> "Add a Django endpoint that takes a group_id and user_id and returns, for each expense in the group, how much that user paid and how much their split was, so we can show them exactly which expenses make up their balance total."

### Prompt 6 — Anomaly Approval Workflow (Meera's requirement)
> "Add approve and reject endpoints for ImportAnomaly objects. Approve should record who approved and when, and update action_taken to auto_fixed. Add a frontend UI with Approve/Reject buttons for any anomaly flagged as requires_approval."

---

## Cases Where AI Was Wrong

### Case 1 — Django 6.0 / CORS Middleware Order
**What AI gave:** Settings file with `CorsMiddleware` in the wrong position.
**What was wrong:** In Django, `CorsMiddleware` must be the very first middleware, before `SecurityMiddleware`. AI placed it after. This caused CORS errors on every preflight request from the React frontend.
**What I changed:** Manually moved `corsheaders.middleware.CorsMiddleware` to the top of the `MIDDLEWARE` list.

---

### Case 2 — Windows `echo.` Command Creates Non-Empty Files
**What AI gave:** `echo. > expenses\urls.py` to create an empty file.
**What was wrong:** On Windows, `echo.` writes a dot and newline into the file, not nothing. Django tried to parse this as Python and crashed with `ImproperlyConfigured: The included URLconf does not appear to have any patterns`.
**What I changed:** Manually opened each urls.py in VS Code and typed the correct `urlpatterns = []` content.

---

### Case 3 — venv Folder Committed to Git
**What AI gave:** Instructions to `git add .` and commit without first creating a `.gitignore`.
**What was wrong:** The entire `venv/` folder (thousands of dependency files, ~50MB) was staged and pushed to GitHub. This made the commit polluted and the repo unusable for others cloning it.
**What I changed:** Created `.gitignore` with `venv/`, `__pycache__/`, `*.pyc`, `.env` entries. Then ran `git rm -r --cached venv/` to remove it from tracking without deleting the local folder.

---

### Case 4 — Balance Breakdown Logic: Incorrect Net Calculation
**What AI gave:** A balance breakdown endpoint that calculated `net = credit - owed` but did not handle the case where a user both paid for an expense AND is in the split (the typical case — you pay upfront for everyone).
**What was wrong:** For a user who paid ₹3000 for a dinner and their own share is ₹750, the correct net is `+3000 - 750 = +2250` (they are owed ₹2250 by others). The AI's initial version returned `credit=3000, owed=750` correctly but then separately displayed them without showing the net contribution clearly. On the frontend, this confused the display when a row showed both a credit and an owed amount.
**What I changed:** Ensured the `net` field always shows `credit - owed` and the frontend renders net with a `+` prefix for positive (gets back) and `-` for negative (owes). Added a totals footer row to make the aggregate clear.

---

### Case 5 — Fuzzy Duplicate Detection Incorrectly Flagged Non-Duplicates
**What AI gave:** A fuzzy duplicate check using `description[:15]` as the key. This was too aggressive — expenses like "Electricity bill February" and "Electricity bill March" share the same first 15 characters and were being flagged as duplicates.
**What was wrong:** The fuzzy key `(date, description[:15])` matched across different months because the date was the only differentiator and both were on different dates — but the key included the date, so these should not match. The real bug: for recurring expenses on the SAME date (unlikely but possible), this would cause false positives.
**What I changed:** Kept the fuzzy check but changed the purpose: it now only adds to `seen_expenses` dict without blocking. Actual skips only happen on exact-key matches. The fuzzy match produces a lower-severity `FUZZY_DUPLICATE` anomaly that is flagged for review but does not skip the row automatically.

---

## AI Limitations Observed

1. **Windows vs Unix commands:** AI consistently suggested Unix shell commands (`touch`, `source`, `export`) that don't work in Windows PowerShell. All commands had to be translated.
2. **Django version drift:** AI's training data includes Django 3.x and 4.x patterns. Some settings and syntax changed in Django 5/6. Had to verify against official docs.
3. **Context loss in long sessions:** In extended conversations, AI forgot earlier decisions (e.g., that we use `amount_inr` not `amount` for balance calculations) and gave inconsistent code. Had to re-state context repeatedly.
4. **Cannot run or test code:** AI cannot execute the code it generates. All correctness verification was done by running the server manually, checking API responses in the browser, and testing the UI.
5. **Overconfident on edge cases:** AI sometimes generated code that handled the happy path correctly but missed edge cases (e.g., what happens when `paid_by` is `None` after a soft delete, or when a split has no members). These were caught during manual testing.
