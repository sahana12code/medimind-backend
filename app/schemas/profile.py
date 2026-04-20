from pydantic import BaseModel, EmailStr


class UserProfileUpdate(BaseModel):
    age: int | None = None
    gender: str | None = None
    medical_condition: str | None = None


class CaregiverCreate(BaseModel):
    name: str
    relation: str | None = None
    phone: str | None = None
    email: EmailStr | None = None
    notify_on_missed: bool = True
