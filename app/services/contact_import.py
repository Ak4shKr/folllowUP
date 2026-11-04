from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.contact import (
    add_contact,
    get_by_email,
    source_fields_changed,
    update_source_fields,
)
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
    dry_run: bool = False,
) -> ImportSummary:
    summary = ImportSummary()
    seen: set[str] = set()

    for row_number, raw_row in enumerate(rows, start=2):
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
        await session.commit()
    return summary
