from datetime import date
from pydantic import BaseModel


class MedicineCreate(BaseModel):
    name: str
    dosage: str | None = None
    medicine_type: str | None = None
    expiry_date: date | None = None
    notes: str | None = None


class OCRResult(BaseModel):
    name: str | None = None
    dosage: str | None = None
    medicine_type: str | None = None
    expiry_date: str | None = None
    raw_text: str | None = None
