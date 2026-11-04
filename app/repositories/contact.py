from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Contact

SOURCE_FIELDS = (
    "name",
    "company_name",
    "designation",
    "company_website",
    "target_role",
    "source",
    "mobile",
)


async def get_by_email(session: AsyncSession, email: str) -> Contact | None:
    result = await session.execute(select(Contact).where(Contact.email == email))
    return result.scalar_one_or_none()


def source_fields_changed(contact: Contact, values: Mapping[str, Any]) -> bool:
    return any(
        values.get(field) not in (None, "") and getattr(contact, field) != values.get(field)
        for field in SOURCE_FIELDS
    )


def update_source_fields(contact: Contact, values: Mapping[str, Any]) -> bool:
    changed = source_fields_changed(contact, values)
    if changed:
        for field in SOURCE_FIELDS:
            value = values.get(field)
            if value not in (None, "") and getattr(contact, field) != value:
                setattr(contact, field, value)
    return changed


async def add_contact(session: AsyncSession, values: Mapping[str, Any]) -> Contact:
    contact = Contact(email=values["email"])
    update_source_fields(contact, values)
    session.add(contact)
    return contact
