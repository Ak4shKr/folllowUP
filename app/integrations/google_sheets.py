from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from google.auth.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from googleapiclient.discovery import build  # type: ignore[import-untyped]


class SheetsValuesClient(Protocol):
    def get(self, *, spreadsheetId: str, range: str) -> "SheetsValuesRequest": ...


class SheetsValuesRequest(Protocol):
    def execute(self) -> dict[str, object]: ...


class SheetsService(Protocol):
    def spreadsheets(self) -> "SheetsResource": ...


class SheetsResource(Protocol):
    def values(self) -> SheetsValuesClient: ...


def load_service_account_credentials(path: Path) -> Credentials:
    return ServiceAccountCredentials.from_service_account_file(
        str(path),
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"],
    )


def build_sheets_service(credentials: Credentials) -> SheetsService:
    return build("sheets", "v4", credentials=credentials, cache_discovery=False)


def fetch_rows(
    service: SheetsService,
    *,
    spreadsheet_id: str,
    source_range: str,
) -> tuple[list[str], list[dict[str, object]]]:
    response = (
        service.spreadsheets()
        .values()
        .get(
            spreadsheetId=spreadsheet_id,
            range=source_range,
        )
        .execute()
    )
    values = response.get("values", [])
    if not isinstance(values, list) or not values:
        return [], []

    header_row = values[0]
    if not isinstance(header_row, list):
        raise ValueError("Google Sheet header row must be a list")

    headers = [str(header).strip() for header in header_row]
    rows: list[dict[str, object]] = []
    for raw_row in values[1:]:
        if not isinstance(raw_row, list):
            raise ValueError("Google Sheet data row must be a list")
        rows.append(
            {
                headers[index]: value
                for index, value in enumerate(raw_row)
                if index < len(headers) and headers[index]
            }
        )
    return headers, rows


def map_headers(
    headers: Sequence[str],
    *,
    field_mapping: dict[str, str],
) -> dict[str, str]:
    normalized_headers = {header.strip().casefold(): header for header in headers}
    mapped: dict[str, str] = {}
    for field, source_header in field_mapping.items():
        source_key = source_header.strip().casefold()
        if source_key not in normalized_headers:
            raise ValueError(f"Configured header {source_header!r} was not found")
        mapped[field] = normalized_headers[source_key]
    if "email" not in mapped:
        raise ValueError("Field mapping must include email")
    return mapped


def map_rows(
    rows: Sequence[dict[str, object]],
    *,
    mapped_headers: dict[str, str],
) -> list[dict[str, object]]:
    return [
        {
            field: row[source_header]
            for field, source_header in mapped_headers.items()
            if source_header in row
        }
        for row in rows
    ]
