from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class FollowupTaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contact_id: UUID
    campaign_id: UUID
    campaign_contact_id: UUID
    previous_email_id: UUID
    sequence_number: int
    due_at: datetime
    status: str
    attempt_count: int
    last_error: str | None
    skip_reason: str | None
    claimed_at: datetime | None
