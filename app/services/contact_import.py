from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.contact import (
    add_contact,
    get_by_email,
    source_fields_changed,
    update_source_fields,
)
from app.repositories.import_run import add_import_run
from app.schemas.contact_import import ContactImportRow


@dataclass
class ImportSummary:
    inserted: int = 0
    updated: int = 0
    unchanged: int = 0
    skipped_duplicate: int = 0
    invalid: list[dict[str, Any]] = field(default_factory=list)
    failed: int = 0


async def import_contacts(
    session: AsyncSession,
    rows: list[dict[str, object]],
    *,
    source: str = "google_sheets",
    sheet_id: str = "",
    source_range: str = "",
    row_numbers: list[int] | None = None,
    dry_run: bool = False,
) -> ImportSummary:
    summary = ImportSummary()
    seen: set[str] = set()
    started_at = datetime.now(UTC)
    source_row_numbers = row_numbers or list(range(2, len(rows) + 2))
    if len(source_row_numbers) != len(rows):
        raise ValueError("row_numbers must match rows length")

    for row_number, raw_row in zip(source_row_numbers, rows, strict=True):
        try:
            row = ContactImportRow.model_validate(raw_row)
        except ValidationError as exc:
            summary.invalid.append({"row": row_number, "reason": exc.errors()})
            continue

        if row.email in seen:
            summary.skipped_duplicate += 1
            continue
        seen.add(row.email)

        values = row.model_dump()
        existing = await get_by_email(session, row.email)
        if existing is None:
            summary.inserted += 1
            if not dry_run:
                await add_contact(session, values)
            continue

        changed = source_fields_changed(existing, values)
        if changed:
            if not dry_run:
                update_source_fields(existing, values)
            summary.updated += 1
        else:
            summary.unchanged += 1

    if not dry_run:
        finished_at = datetime.now(UTC)
        await add_import_run(
            session,
            source=source,
            sheet_id=sheet_id,
            source_range=source_range,
            started_at=started_at,
            finished_at=finished_at,
            inserted=summary.inserted,
            updated=summary.updated,
            unchanged=summary.unchanged,
            skipped_duplicate=summary.skipped_duplicate,
            invalid=len(summary.invalid),
            failed=summary.failed,
            details={"invalid_rows": summary.invalid},
        )
        await session.commit()
    return summary
