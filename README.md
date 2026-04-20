# MediMind Backend (FastAPI)

## Run locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API base URL: `http://127.0.0.1:8000`

Default database is SQLite for quick setup. Change `DATABASE_URL` in `.env` if you want PostgreSQL.
