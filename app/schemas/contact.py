from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator


class ContactCreate(BaseModel):
    email: EmailStr
    name: str | None = None
    company_name: str | None = None
    designation: str | None = None
    company_website: str | None = None
    target_role: str | None = None
    source: str | None = None
    mobile: str | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class ContactUpdate(BaseModel):
    name: str | None = None
    company_name: str | None = None
    designation: str | None = None
    company_website: str | None = None
    target_role: str | None = None
    source: str | None = None
    mobile: str | None = None


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    name: str | None
    company_name: str | None
    designation: str | None
    company_website: str | None
    target_role: str | None
    source: str | None
    mobile: str | None
    status: str
