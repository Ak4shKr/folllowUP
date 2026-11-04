from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class JobProfileFields(BaseModel):
    name: str = Field(min_length=1)
    target_roles: list[str] = Field(default_factory=list)
    skills: list[str] = Field(default_factory=list)
    experience_summary: str | None = None
    resume_text: str | None = None
    resume_reference: str | None = None
    is_active: bool = True


class JobProfileCreate(JobProfileFields):
    pass


class JobProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    target_roles: list[str] | None = None
    skills: list[str] | None = None
    experience_summary: str | None = None
    resume_text: str | None = None
    resume_reference: str | None = None
    is_active: bool | None = None


class JobProfileResponse(JobProfileFields):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
