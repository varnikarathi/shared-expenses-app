 # AI_USAGE.md — AI Collaboration Log

## AI Tool Used
**Claude (Anthropic)** — claude.ai
Used as primary development collaborator throughout the entire project.

---

## How AI Was Used

Claude was used to:
- Plan the project architecture and database schema
- Generate boilerplate Django models, serializers, views, and URLs
- Generate React page components and CSS
- Design the CSV anomaly detection logic
- Write documentation (README, SCOPE, DECISIONS)

All code was reviewed, understood, and in several cases corrected before use.

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

---

## Cases Where AI Was Wrong

### Case 1 — Django 6.0 Compatibility Issue
**What AI gave:** Settings file with `DEFAULT_AUTO_FIELD` and standard middleware.
**What was wrong:** AI initially suggested `django.middleware.common.CommonMiddleware` before `corsheaders.middleware.CorsMiddleware`. In Django 6.0, CORS middleware must be first or CORS headers are not added to responses.
**What I changed:** Moved `corsheaders.middleware.CorsMiddleware` to the top of the MIDDLEWARE list.

### Case 2 — Empty URL Files Caused Server Crash
**What AI gave:** Instructions to create empty `urls.py` files for groups, expenses, importer apps using `echo. > filename`.
**What was wrong:** The `echo.` command on Windows creates a file with content (a dot and newline), not an empty file. Django tried to parse this as Python and crashed with `ImproperlyConfigured: The included URLconf does not appear to have any patterns`.
**What I changed:** Manually opened each urls.py in VS Code and replaced the content with proper `urlpatterns = []`.

### Case 3 — venv Folder Committed to Git
**What AI gave:** Instructions to `git add .` and commit without first creating a `.gitignore`.
**What was wrong:** The entire `venv/` folder (thousands of files) was staged and pushed to GitHub, making the commit history polluted and the repo huge.
**What I changed:** Added `.gitignore` with `venv/`, `__pycache__/`, `*.pyc`, `.env` entries. Then ran `git rm -r --cached venv/` to remove it from tracking.

### Case 4 — IndentationError in expenses/urls.py
**What AI gave:** Command `echo. > expenses\urls.py` to create the file.
**What was wrong:** The Windows `echo.` command added unexpected content causing an IndentationError when Django tried to import the file.
**What I changed:** Manually typed the correct content in VS Code.

---

## AI Limitations Observed

1. **Windows vs Mac differences:** AI sometimes gave Unix commands (like `touch` or `source`) that don't work on Windows. Had to translate to Windows equivalents.
2. **Django version differences:** AI's training data includes older Django versions. Some syntax and settings differ in Django 6.0.
3. **Context loss:** In a long conversation, AI sometimes forgot earlier decisions and gave inconsistent advice. Had to re-state context.
4. **Cannot run code:** AI cannot actually test the code it generates. All testing was done manually by running the server and checking outputs.
