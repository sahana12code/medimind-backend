from __future__ import annotations

from twilio.base.exceptions import TwilioException
from twilio.rest import Client

from app.core.config import settings
from app.models.models import AdherenceLog, Caregiver, Reminder, User


def send_caregiver_alert(
    user: User,
    caregiver: Caregiver,
    reminder: Reminder,
    log: AdherenceLog,
) -> bool:
    if not caregiver.notify_on_missed:
        return False

    if not caregiver.phone:
        return False

    if (
        not settings.twilio_enabled
        or not settings.twilio_account_sid
        or not settings.twilio_auth_token
        or not settings.twilio_from_number
    ):
        return False

    due_time = log.effective_due_at or log.scheduled_for
    scheduled_time = due_time.strftime("%Y-%m-%d %H:%M")

    medicine_name = "Medicine"
    dosage = "Not specified"

    if reminder.medicine:
        medicine_name = reminder.medicine.name or "Medicine"
        dosage = reminder.medicine.dosage or "Not specified"

    message_body = (
        f"Missed medicine alert for {user.full_name}. "
        f"Medicine: {medicine_name}. "
        f"Dosage: {dosage}. "
        f"Scheduled for: {scheduled_time}. "
        f"Status: missed. Please check on them."
    )

    try:
        client = Client(
            settings.twilio_account_sid,
            settings.twilio_auth_token,
        )

        sms = client.messages.create(
            body=message_body,
            from_=settings.twilio_from_number,
            to=caregiver.phone,
        )

        return bool(sms.sid)

    except TwilioException as error:
        print(f"Twilio SMS failed for caregiver {caregiver.id}: {error}")
        return False

    except Exception as error:
        print(f"Unexpected caregiver alert error for caregiver {caregiver.id}: {error}")
        return False