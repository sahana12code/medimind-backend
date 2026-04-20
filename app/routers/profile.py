from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Caregiver, User
from app.routers.deps import get_current_user
from app.schemas.profile import CaregiverCreate, UserProfileUpdate

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("")
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    caregivers = db.query(Caregiver).filter(Caregiver.user_id == current_user.id).all()
    return {
        "id": current_user.id,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "age": current_user.age,
        "gender": current_user.gender,
        "medical_condition": current_user.medical_condition,
        "caregivers": [
            {
                "id": item.id,
                "name": item.name,
                "relation": item.relation,
                "phone": item.phone,
                "email": item.email,
                "notify_on_missed": item.notify_on_missed,
            }
            for item in caregivers
        ],
    }


@router.put("")
def update_profile(
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    current_user.age = payload.age
    current_user.gender = payload.gender
    current_user.medical_condition = payload.medical_condition
    db.commit()
    db.refresh(current_user)
    return {"message": "Profile updated successfully"}


@router.post("/caregiver")
def add_caregiver(
    payload: CaregiverCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    caregiver = db.query(Caregiver).filter(Caregiver.user_id == current_user.id).order_by(Caregiver.id.asc()).first()
    if caregiver:
        caregiver.name = payload.name
        caregiver.relation = payload.relation
        caregiver.phone = payload.phone
        caregiver.email = payload.email
        caregiver.notify_on_missed = payload.notify_on_missed
        db.commit()
        db.refresh(caregiver)
        return {"message": "Caregiver updated successfully", "id": caregiver.id}

    caregiver = Caregiver(user_id=current_user.id, **payload.model_dump())
    db.add(caregiver)
    db.commit()
    db.refresh(caregiver)
    return {"message": "Caregiver added successfully", "id": caregiver.id}
