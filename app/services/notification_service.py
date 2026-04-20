from __future__ import annotations

import smtplib
from email.message import EmailMessage

from app.core.config import settings
from app.models.models import AdherenceLog, Caregiver, Reminder, User


def send_caregiver_alert(user: User, caregiver: Caregiver, reminder: Reminder, log: AdherenceLog) -> bool:
    if not caregiver.notify_on_missed or not caregiver.email:
        return False
    if not settings.smtp_enabled or not settings.smtp_host or not settings.smtp_username or not settings.smtp_password or not settings.smtp_from_email:
        return False

    message = EmailMessage()
    message["Subject"] = f"Missed medicine alert for {user.full_name}"
    message["From"] = settings.smtp_from_email
    message["To"] = caregiver.email
    scheduled_time = log.scheduled_for.strftime("%Y-%m-%d %H:%M")
    message.set_content(
        f"Hello {caregiver.name},\n\n"
        f"{user.full_name} missed the scheduled medicine dose.\n\n"
        f"Medicine: {reminder.medicine.name}\n"
        f"Dosage: {reminder.medicine.dosage or 'Not specified'}\n"
        f"Scheduled for: {scheduled_time}\n"
        f"Status: missed\n\n"
        "Please check in with them as soon as possible.\n\n"
        "Regards,\nMediMind"
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        if settings.smtp_use_tls:
            server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(message)
    return True
