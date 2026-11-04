import pytest
from pydantic import ValidationError

from app.schemas.contact import ContactCreate
from app.schemas.contact_import import ContactImportRow


def test_contact_email_is_trimmed_and_lowercase() -> None:
    contact = ContactCreate(email="  Person@Example.COM ")

    assert contact.email == "person@example.com"


def test_import_row_ignores_unknown_columns_and_preserves_mobile_text() -> None:
    row = ContactImportRow.model_validate(
        {"email": "person@example.com", "mobile": 9876543210, "unknown": "ignored"}
    )

    assert row.mobile == "9876543210"


@pytest.mark.parametrize("email", ["", "person", "person@example", "a@@example.com"])
def test_import_row_rejects_invalid_email(email: str) -> None:
    with pytest.raises(ValidationError):
        ContactImportRow(email=email)
