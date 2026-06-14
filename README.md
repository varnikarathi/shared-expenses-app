# Shared Expenses App — SplitApp

A full-stack shared expense tracking app built for the Spreetail internship assignment.
Handles messy real-world expense data: duplicate entries, currency mismatches, membership changes, and settlements disguised as expenses.

## 🌐 Live Demo

**https://shared-expense.up.railway.app**

## 📁 GitHub Repository

https://github.com/varnikarathi/shared-expenses-app

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 5.x + Django REST Framework |
| Database | PostgreSQL (Railway managed) |
| Frontend | React.js (served as static build via WhiteNoise) |
| Auth | JWT (djangorestframework-simplejwt) |
| Deployment | Railway |
| AI Used | Claude (Anthropic) — claude.ai |

## ✅ Features

- **Login / Register** — Email-based JWT authentication
- **Groups** — Create and manage groups with time-based membership (members join and leave with tracked dates)
- **Expenses** — Add expenses with 4 split types:
  - Equal split
  - Unequal (exact amounts per person)
  - Percentage split
  - By Share (ratio-based)
- **Multi-currency** — USD expenses converted to INR at fixed rate ₹83.5/USD; original amount always stored
- **Balances** — Individual balance summary per person (who gets back / who owes)
- **Settlement Suggestions** — Minimum-transaction greedy algorithm (Aisha's "one number per person" requirement)
- **Settlements** — Record debt payments between members
- **CSV Import** — Ingest `expenses_export.csv` with full anomaly detection (20 anomaly types detected)
- **Import Report** — Live anomaly log shown in-app: every problem found, colour-coded by action taken

## 📐 Database Schema (Summary)

```
users_user           → id, email, username, password (AbstractUser, email-login)
groups_group         → id, name, description, created_by
groups_groupmembership → id, group, user, joined_at, left_at, is_active
expenses_expense     → id, group, description, amount, currency, amount_inr, paid_by, date, split_type, notes, is_deleted, import_row
expenses_expensesplit → id, expense, user, amount_owed, percentage, shares
expenses_settlement  → id, group, paid_by, paid_to, amount, currency, date, notes
importer_importsession → id, filename, imported_by, imported_at, status, total_rows, imported_rows, skipped_rows, report
importer_importanomaly → id, session, row_number, raw_data, anomaly_type, description, action_taken, resolution, requires_approval
```

Full schema with column-level detail: see [SCOPE.md](SCOPE.md)

## 🚀 Setup Instructions

### Prerequisites
- Python 3.12+
- Node.js 18+
- PostgreSQL 14+

### 1. Clone the repo

```bash
git clone https://github.com/varnikarathi/shared-expenses-app.git
cd shared-expenses-app
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv

# Windows
venv\Scripts\activate

# Mac/Linux
source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file inside the `backend/` folder:

```env
DB_NAME=shared_expenses
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=your-secret-key-here
DEBUG=True
```

Run migrations and start the server:

```bash
python manage.py migrate
python manage.py runserver
```

Backend runs at: `http://127.0.0.1:8000`

### 3. Frontend Setup

```bash
cd frontend
npm install
npm start
```

Frontend dev server runs at: `http://localhost:3000`

> For production, the React app is built and served by Django via WhiteNoise:
> ```bash
> cd frontend && npm run build
> ```
> Then Railway picks it up via `Procfile`.

### 4. Create Users

Register users via the app at `/register`. For the CSV import to work correctly, create accounts for all flatmates:
- **Aisha**, **Rohan**, **Priya**, **Meera**, **Dev**, **Sam**

(Usernames must match exactly — the importer does case-insensitive + fuzzy matching)

### 5. Set Up Group Membership Dates

After creating the group and adding all members, use "Add Member" with the correct join dates:
- Aisha, Rohan, Priya: **01-02-2026** (February start)
- Meera: joined **01-02-2026**, left **31-03-2026**
- Dev: **01-02-2026** (temporary / trip member)
- Sam: joined **15-04-2026**

This is critical: the importer checks these dates to flag expenses where Meera appears after she left, or Sam appears before he joined.

### 6. Import CSV

1. Login and create a group
2. Add all members with correct join dates
3. Go to **Import CSV** page
4. Select group and upload `expenses_export.csv`
5. View the import report — every anomaly is listed with action taken

## 📡 API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/users/register/` | Register new user |
| POST | `/api/users/login/` | Login (returns JWT) |
| GET | `/api/users/profile/` | Get current user profile |
| GET | `/api/users/list/` | List all users |

### Groups
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/groups/` | List / Create groups |
| GET/PUT/DELETE | `/api/groups/<id>/` | Group detail |
| POST | `/api/groups/<id>/add-member/` | Add member with join date |
| POST | `/api/groups/<id>/remove-member/` | Remove member with leave date |

### Expenses
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/api/expenses/<group_id>/expenses/` | List / Create expenses |
| GET/PUT/DELETE | `/api/expenses/<group_id>/expenses/<id>/` | Expense detail |
| GET | `/api/expenses/<group_id>/balances/` | Individual balances |
| GET | `/api/expenses/<group_id>/settlement-suggestions/` | Who pays whom |
| GET/POST | `/api/expenses/<group_id>/settlements/` | List / Record settlements |

### Import
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/import/` | Upload and import CSV |
| GET | `/api/import/report/<session_id>/` | Get import report |

## 🤖 AI Used

**Claude (Anthropic)** — claude.ai was used as the primary development collaborator.
See [AI_USAGE.md](AI_USAGE.md) for full usage log, key prompts, and documented cases where AI output was wrong and corrected.

## 📋 Documentation

| File | Contents |
|------|----------|
| [SCOPE.md](SCOPE.md) | Full database schema + all 20 anomalies found in the CSV and how each was handled |
| [DECISIONS.md](DECISIONS.md) | 12 engineering decision logs with options considered and rationale |
| [AI_USAGE.md](AI_USAGE.md) | AI prompts, usage patterns, and 4+ cases where AI was wrong |
