from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CampaignEnrollmentCreate(BaseModel):
    contact_id: UUID


class CampaignEnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    campaign_id: UUID
    contact_id: UUID
    status: str
    stopped_reason: str | None
    sequence_base: int
