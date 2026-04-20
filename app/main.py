from contextlib import asynccontextmanager
from datetime import date

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import Base, SessionLocal, engine
from app.models.models import User
from app.routers import auth, dashboard, medicines, profile, reminders
from app.routers.reminders import sync_user_logs

Base.metadata.create_all(bind=engine)

scheduler = BackgroundScheduler()


def run_reminder_sync_job():
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()

        for user in users:
            try:
                sync_user_logs(user, db, today=date.today())
            except Exception as user_error:
                print(f"Reminder sync failed for user {user.id}: {user_error}")

    except Exception as error:
        print(f"Background reminder sync job failed: {error}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_started = False

    try:
        if settings.scheduler_enabled:
            scheduler.add_job(
                run_reminder_sync_job,
                trigger="interval",
                minutes=settings.scheduler_interval_minutes,
                id="reminder_sync_job",
                replace_existing=True,
                max_instances=1,
            )
            scheduler.start()
            scheduler_started = True
            print(
                f"Reminder scheduler started. Running every "
                f"{settings.scheduler_interval_minutes} minute(s)."
            )
        else:
            print("Reminder scheduler is disabled.")

        yield

    finally:
        if scheduler_started and scheduler.running:
            scheduler.shutdown()
            print("Reminder scheduler stopped.")


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(medicines.router)
app.include_router(reminders.router)
app.include_router(dashboard.router)


@app.get("/")
def root():
    return {"message": "MediMind API is running"}