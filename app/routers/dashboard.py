from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Medicine, User
from app.routers.deps import get_current_user
from app.routers.reminders import sync_user_logs

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("")
def dashboard(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    today = date.today()
    medicines_count = db.query(Medicine).filter(Medicine.user_id == current_user.id).count()
    today_schedule = sync_user_logs(current_user, db, today=today)

    today_taken = sum(1 for item in today_schedule if item["status"] == "taken")
    today_missed = sum(1 for item in today_schedule if item["status"] == "missed")
    today_pending = sum(1 for item in today_schedule if item["status"] in {"pending", "snoozed"})

    completed_total = sum(1 for item in today_schedule if item["status"] in {"taken", "missed", "skipped"})
    taken_total = sum(1 for item in today_schedule if item["status"] == "taken")
    adherence_rate = round((taken_total / completed_total) * 100, 1) if completed_total else 100.0

    next_reminder = next((item for item in today_schedule if item["status"] in {"pending", "snoozed"}), None)

    return {
        "greeting": f"Hello, {current_user.full_name.split()[0]}",
        "today_medicines": medicines_count,
        "today_taken": today_taken,
        "today_missed": today_missed,
        "today_pending": today_pending,
        "adherence_rate": adherence_rate,
        "next_reminder": next_reminder,
        "today_schedule": today_schedule,
    }
