from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ImportRun


async def add_import_run(
    session: AsyncSession,
    *,
    source: str,
    sheet_id: str,
    source_range: str,
    started_at: datetime,
    finished_at: datetime,
    inserted: int,
    updated: int,
    unchanged: int,
    skipped_duplicate: int,
    invalid: int,
    failed: int,
    details: dict[str, Any],
) -> ImportRun:
    import_run = ImportRun(
        source=source,
        sheet_id=sheet_id,
        range=source_range,
        started_at=started_at,
        finished_at=finished_at,
        inserted=inserted,
        updated=updated,
        unchanged=unchanged,
        skipped_duplicate=skipped_duplicate,
        invalid=invalid,
        failed=failed,
        details=details,
    )
    session.add(import_run)
    return import_run
