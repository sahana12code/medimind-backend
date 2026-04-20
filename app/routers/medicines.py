from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.models import Medicine, User
from app.routers.deps import get_current_user
from app.schemas.medicine import MedicineCreate
from app.services.ocr_service import extract_text_from_bytes, parse_medicine_text

router = APIRouter(prefix="/medicines", tags=["medicines"])


@router.get("")
def list_medicines(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    items = (
        db.query(Medicine)
        .filter(Medicine.user_id == current_user.id)
        .order_by(Medicine.created_at.desc())
        .all()
    )
    return [
        {
            "id": item.id,
            "name": item.name,
            "dosage": item.dosage,
            "medicine_type": item.medicine_type,
            "expiry_date": item.expiry_date.isoformat() if item.expiry_date else None,
            "notes": item.notes,
        }
        for item in items
    ]


@router.post("")
def create_medicine(
    payload: MedicineCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    medicine = Medicine(user_id=current_user.id, **payload.model_dump())
    db.add(medicine)
    db.commit()
    db.refresh(medicine)
    return {"message": "Medicine added successfully", "id": medicine.id}


@router.post("/scan")
async def scan_medicine(
    image: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    image_bytes = await image.read()
    text = extract_text_from_bytes(image_bytes)
    result = parse_medicine_text(text)
    return result
