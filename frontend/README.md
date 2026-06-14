# Shared Expenses App — Splitwise Clone

A full-stack shared expense tracking app built for the Spreetail internship assignment.

## Live Demo
Coming soon (deployment in progress)

## GitHub Repository
https://github.com/varnikarathi/shared-expenses-app

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Django 6.0 + Django REST Framework |
| Database | PostgreSQL 16 |
| Frontend | React.js |
| Auth | JWT (djangorestframework-simplejwt) |
| AI Used | Claude (Anthropic) — claude.ai |

## Features

- User registration and login with JWT auth
- Create and manage groups with time-based membership (members join and leave)
- Add expenses with 4 split types: Equal, Unequal, Percentage, By Share
- USD to INR currency conversion (fixed rate: ₹83.5 per USD)
- Group balances and individual balance summary
- Debt settlement suggestions using minimum transactions algorithm
- Record settlements/payments
- CSV import with full anomaly detection (14 anomalies detected in sample CSV)
- Detailed import report showing every anomaly and action taken

## Setup Instructions

### Prerequisites
- Python 3.12+
- Node.js 22+
- PostgreSQL 16

### Backend Setup

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
```
DB_NAME=shared_expenses
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5433
SECRET_KEY=your-secret-key-here
```

Run migrations and start the server:
```bash
python manage.py migrate
python manage.py runserver
```

Backend runs at: `http://127.0.0.1:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm start
```

Frontend runs at: `http://localhost:3000`

### Create Users

Register users via the app at `/register`. For the CSV import to work correctly, register:
- Aisha, Rohan, Priya, Meera, Dev, Sam

### Import CSV

1. Login and create a group
2. Add all members with correct join dates
3. Go to Import CSV page
4. Select group and upload `expenses_export.csv`
5. View the import report

## API Endpoints

### Auth
- `POST /api/users/register/` — Register
- `POST /api/users/login/` — Login
- `GET /api/users/profile/` — Get profile
- `GET /api/users/list/` — List all users

### Groups
- `GET/POST /api/groups/` — List/Create groups
- `GET/PUT/DELETE /api/groups/<id>/` — Group detail
- `POST /api/groups/<id>/add-member/` — Add member
- `POST /api/groups/<id>/remove-member/` — Remove member

### Expenses
- `GET/POST /api/expenses/<group_id>/expenses/` — List/Create expenses
- `GET/PUT/DELETE /api/expenses/<group_id>/expenses/<id>/` — Expense detail
- `GET /api/expenses/<group_id>/balances/` — Group balances
- `GET /api/expenses/<group_id>/settlements/` — Settlements
- `GET /api/expenses/<group_id>/settlement-suggestions/` — Who pays whom

### Import
- `POST /api/import/` — Import CSV
- `GET /api/import/report/<session_id>/` — Get import report

## AI Used

**Claude (Anthropic)** — claude.ai was used as the primary development collaborator.
See `AI_USAGE.md` for detailed usage log including cases where AI was wrong.