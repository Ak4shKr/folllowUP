from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EmailMessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    contact_id: UUID
    campaign_id: UUID
    campaign_contact_id: UUID
    parent_email_id: UUID | None
    email_type: str
    sequence_number: int
    subject: str
    body: str
    status: str
    scheduled_at: datetime | None
    sent_at: datetime | None
    provider_message_id: str | None
    provider_thread_id: str | None
    attempt_count: int
    skip_reason: str | None
    prompt_version: str | None
    model_name: str | None
    input_fingerprint: str | None
    approved_at: datetime | None
