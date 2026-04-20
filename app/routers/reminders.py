from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.database import get_db
from app.models.models import AdherenceLog, Caregiver, Medicine, Reminder, User
from app.routers.deps import get_current_user
from app.schemas.reminder import AdherenceAction, ReminderCreate
from app.services.notification_service import send_caregiver_alert

router = APIRouter(prefix="/reminders", tags=["reminders"])


STATUS_PRIORITY = {"missed": 0, "pending": 1, "snoozed": 2, "taken": 3, "skipped": 4}


def _matches_frequency(reminder: Reminder, target_date: date) -> bool:
    freq = (reminder.frequency or "").strip().lower()

    if freq in {"once daily", "daily", "every day", "everyday"}:
        return True

    if freq in {"alternate day", "alternate days", "every other day"}:
        delta_days = (target_date - reminder.start_date).days
        return delta_days >= 0 and delta_days % 2 == 0

    if freq in {"weekly", "once weekly"}:
        return target_date.weekday() == reminder.start_date.weekday()

    if freq in {"mon-fri", "monday-friday", "weekdays"}:
        return target_date.weekday() < 5

    if freq in {"sat-sun", "weekends"}:
        return target_date.weekday() >= 5

    return True


def _reminder_active_for_day(reminder: Reminder, target_date: date) -> bool:
    if reminder.status != "active":
        return False

    if reminder.start_date > target_date:
        return False

    if reminder.end_date is not None and reminder.end_date < target_date:
        return False

    return _matches_frequency(reminder, target_date)


def _scheduled_datetime(reminder: Reminder, target_date: date) -> datetime:
    return datetime.combine(target_date, reminder.reminder_time)


def _trigger_caregiver_alerts(user: User, reminder: Reminder, log: AdherenceLog, db: Session) -> bool:
    alert_sent = False
    caregivers = db.query(Caregiver).filter(Caregiver.user_id == user.id).all()

    for caregiver in caregivers:
        try:
            sent = send_caregiver_alert(user, caregiver, reminder, log)
            alert_sent = alert_sent or sent
        except Exception:
            continue

    return alert_sent


def sync_user_logs(current_user: User, db: Session, today: date | None = None) -> list[dict]:
    today = today or date.today()
    now = datetime.now()

    reminders = (
        db.query(Reminder)
        .options(joinedload(Reminder.medicine))
        .filter(Reminder.user_id == current_user.id)
        .all()
    )

    changed = False
    rows: list[dict] = []
    cutoff = now - timedelta(minutes=settings.reminder_grace_minutes)

    for reminder in reminders:
        if not _reminder_active_for_day(reminder, today):
            continue

        scheduled_for = _scheduled_datetime(reminder, today)

        log = (
            db.query(AdherenceLog)
            .filter(
                AdherenceLog.reminder_id == reminder.id,
                AdherenceLog.scheduled_for == scheduled_for,
            )
            .first()
        )

        if not log:
            log = AdherenceLog(
                user_id=current_user.id,
                medicine_id=reminder.medicine_id,
                reminder_id=reminder.id,
                scheduled_for=scheduled_for,
                effective_due_at=scheduled_for,
                snoozed_until=None,
                status="pending",
            )
            db.add(log)
            db.flush()
            changed = True

        due_at = log.effective_due_at or log.scheduled_for

        if log.status in {"pending", "snoozed"} and due_at <= cutoff:
            log.status = "missed"
            log.snoozed_until = None

            if not log.caregiver_alert_sent:
                log.caregiver_alert_sent = _trigger_caregiver_alerts(current_user, reminder, log, db)
                if log.caregiver_alert_sent:
                    log.alert_sent_at = datetime.utcnow()

            changed = True

        rows.append(
            {
                "id": log.id,
                "reminder_id": reminder.id,
                "medicine_id": reminder.medicine_id,
                "medicine_name": reminder.medicine.name,
                "dosage": reminder.medicine.dosage,
                "frequency": reminder.frequency,
                "time_label": reminder.time_label,
                "scheduled_for": log.scheduled_for.isoformat(),
                "effective_due_at": due_at.isoformat(),
                "snoozed_until": log.snoozed_until.isoformat() if log.snoozed_until else None,
                "display_time": due_at.strftime("%I:%M %p"),
                "status": log.status,
                "snooze_count": log.snooze_count,
                "caregiver_alert_sent": log.caregiver_alert_sent,
            }
        )

    if changed:
        db.commit()
    else:
        db.flush()

    rows.sort(key=lambda item: (item["effective_due_at"], STATUS_PRIORITY.get(item["status"], 99)))
    return rows


@router.get("")
def list_reminders(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    reminders = (
        db.query(Reminder)
        .options(joinedload(Reminder.medicine))
        .filter(Reminder.user_id == current_user.id)
        .order_by(Reminder.reminder_time.asc())
        .all()
    )

    return [
        {
            "id": reminder.id,
            "medicine_id": reminder.medicine_id,
            "medicine_name": reminder.medicine.name,
            "dosage": reminder.medicine.dosage,
            "frequency": reminder.frequency,
            "time_label": reminder.time_label,
            "reminder_time": reminder.reminder_time.isoformat(),
            "start_date": reminder.start_date.isoformat(),
            "end_date": reminder.end_date.isoformat() if reminder.end_date else None,
            "status": reminder.status,
        }
        for reminder in reminders
    ]


@router.get("/today")
def today_schedule(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return sync_user_logs(current_user, db)


@router.get("/history")
def reminder_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sync_user_logs(current_user, db)

    logs = (
        db.query(AdherenceLog)
        .options(joinedload(AdherenceLog.medicine), joinedload(AdherenceLog.reminder))
        .filter(AdherenceLog.user_id == current_user.id)
        .order_by(AdherenceLog.scheduled_for.desc())
        .all()
    )

    return [
        {
            "id": log.id,
            "medicine_name": log.medicine.name,
            "dosage": log.medicine.dosage,
            "scheduled_for": log.scheduled_for.isoformat(),
            "effective_due_at": (log.effective_due_at or log.scheduled_for).isoformat(),
            "snoozed_until": log.snoozed_until.isoformat() if log.snoozed_until else None,
            "display_time": (log.effective_due_at or log.scheduled_for).strftime("%d %b %Y • %I:%M %p"),
            "status": log.status,
            "taken_at": log.taken_at.isoformat() if log.taken_at else None,
            "time_label": log.reminder.time_label,
            "caregiver_alert_sent": log.caregiver_alert_sent,
            "snooze_count": log.snooze_count,
            "alert_sent_at": log.alert_sent_at.isoformat() if log.alert_sent_at else None,
        }
        for log in logs
    ]


@router.post("/sync")
def sync_reminders(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = sync_user_logs(current_user, db)
    return {"message": "Reminder schedule synced", "items": items}


@router.post("")
def create_reminder(
    payload: ReminderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    medicine = db.get(Medicine, payload.medicine_id)
    if not medicine or medicine.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Medicine not found")

    reminder = Reminder(user_id=current_user.id, **payload.model_dump())
    db.add(reminder)
    db.commit()
    db.refresh(reminder)

    sync_user_logs(current_user, db)

    return {"message": "Reminder created successfully", "id": reminder.id}


@router.post("/action")
def reminder_action(
    payload: AdherenceAction,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reminder = (
        db.query(Reminder)
        .options(joinedload(Reminder.medicine))
        .filter(Reminder.id == payload.reminder_id, Reminder.user_id == current_user.id)
        .first()
    )
    if not reminder:
        raise HTTPException(status_code=404, detail="Reminder not found")

    scheduled_for = datetime.fromisoformat(payload.scheduled_for)

    log = (
        db.query(AdherenceLog)
        .filter(
            AdherenceLog.reminder_id == reminder.id,
            AdherenceLog.scheduled_for == scheduled_for,
        )
        .first()
    )

    if not log:
        log = AdherenceLog(
            user_id=current_user.id,
            medicine_id=reminder.medicine_id,
            reminder_id=reminder.id,
            scheduled_for=scheduled_for,
            effective_due_at=scheduled_for,
            snoozed_until=None,
            status="pending",
        )
        db.add(log)
        db.flush()

    log.status = payload.status

    if payload.status == "taken":
        log.taken_at = datetime.utcnow()
        log.snoozed_until = None
        log.effective_due_at = log.scheduled_for

    elif payload.status == "snoozed":
        minutes = payload.snooze_minutes or 10
        now = datetime.utcnow()
        base_time = log.effective_due_at or log.scheduled_for
        next_due = max(now, base_time) + timedelta(minutes=minutes)

        log.snooze_count += 1
        log.snoozed_until = next_due
        log.effective_due_at = next_due
        log.taken_at = None

    elif payload.status == "missed":
        log.snoozed_until = None
        if not log.caregiver_alert_sent:
            log.caregiver_alert_sent = _trigger_caregiver_alerts(current_user, reminder, log, db)
            if log.caregiver_alert_sent:
                log.alert_sent_at = datetime.utcnow()

    elif payload.status == "skipped":
        log.taken_at = None
        log.snoozed_until = None
        log.effective_due_at = log.scheduled_for

    db.commit()

    return {
        "message": "Reminder action saved",
        "status": log.status,
        "caregiver_alert_sent": log.caregiver_alert_sent,
        "snooze_until": log.snoozed_until.isoformat() if log.snoozed_until else None,
        "effective_due_at": (log.effective_due_at or log.scheduled_for).isoformat(),
    }