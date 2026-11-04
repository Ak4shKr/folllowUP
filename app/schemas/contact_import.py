from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContactImportRow(BaseModel):
    model_config = ConfigDict(extra="ignore")

    email: str = Field(min_length=1, max_length=254)
    name: str | None = None
    company_name: str | None = None
    designation: str | None = None
    company_website: str | None = None
    target_role: str | None = None
    source: str | None = None
    mobile: str | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("email is required")
        if any(ord(character) < 32 or ord(character) == 127 for character in normalized):
            raise ValueError("email contains a control character")
        if normalized.count("@") != 1:
            raise ValueError("email must contain one @")
        local, domain = normalized.split("@")
        if not local or not domain or "." not in domain:
            raise ValueError("email format is invalid")
        return normalized

    @field_validator("mobile", mode="before")
    @classmethod
    def preserve_mobile_as_text(cls, value: object) -> str | None:
        if value is None or value == "":
            return None
        return str(value)
