from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ImportRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source: str
    sheet_id: str
    range: str
    started_at: datetime
    finished_at: datetime | None
    inserted: int
    updated: int
    unchanged: int
    skipped_duplicate: int
    invalid: int
    failed: int
    details: dict[str, Any]
