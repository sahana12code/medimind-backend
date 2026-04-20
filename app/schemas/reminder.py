from datetime import date, time
from pydantic import BaseModel, Field


class ReminderCreate(BaseModel):
    medicine_id: int
    frequency: str
    time_label: str | None = None
    reminder_time: time
    start_date: date
    end_date: date | None = None


class AdherenceAction(BaseModel):
    reminder_id: int
    status: str = Field(pattern="^(taken|snoozed|skipped|missed)$")
    scheduled_for: str
    snooze_minutes: int | None = 10
