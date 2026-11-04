from datetime import time
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CampaignFields(BaseModel):
    name: str = Field(min_length=1)
    job_profile_id: UUID
    email_mode: str = "personalized"
    status: str = "draft"
    daily_limit: int = Field(default=50, ge=1, le=50)
    followup_interval_days: int = Field(default=4, ge=1)
    max_followups: int = Field(default=2, ge=0, le=5)
    timezone: str = "Asia/Kolkata"
    sending_window_start: time | None = time(9, 0)
    sending_window_end: time | None = time(18, 0)

    @model_validator(mode="after")
    def validate_window(self) -> "CampaignFields":
        if (self.sending_window_start is None) != (self.sending_window_end is None):
            raise ValueError("sending window start and end must both be set or both be empty")
        return self


class CampaignCreate(CampaignFields):
    pass


class CampaignUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    job_profile_id: UUID | None = None
    email_mode: str | None = None
    status: str | None = None
    daily_limit: int | None = Field(default=None, ge=1, le=50)
    followup_interval_days: int | None = Field(default=None, ge=1)
    max_followups: int | None = Field(default=None, ge=0, le=5)
    timezone: str | None = None
    sending_window_start: time | None = None
    sending_window_end: time | None = None


class CampaignResponse(CampaignFields):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
