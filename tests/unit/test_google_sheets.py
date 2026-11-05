import pytest

from app.integrations.google_sheets import fetch_rows, map_headers, map_rows


class FakeRequest:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response

    def execute(self) -> dict[str, object]:
        return self.response


class FakeValues:
    def __init__(self, response: dict[str, object]) -> None:
        self.response = response
        self.request: tuple[str, str] | None = None

    def get(self, *, spreadsheetId: str, range: str) -> FakeRequest:
        self.request = (spreadsheetId, range)
        return FakeRequest(self.response)


class FakeSpreadsheets:
    def __init__(self, response: dict[str, object]) -> None:
        self._values = FakeValues(response)

    def values(self) -> FakeValues:
        return self._values


class FakeService:
    def __init__(self, response: dict[str, object]) -> None:
        self._spreadsheets = FakeSpreadsheets(response)

    def spreadsheets(self) -> FakeSpreadsheets:
        return self._spreadsheets


def test_fetch_rows_reads_headers_and_pads_short_rows() -> None:
    service = FakeService(
        {"values": [["Email", "Name", "Mobile"], ["person@example.com", "Person"]]}
    )

    headers, rows = fetch_rows(service, spreadsheet_id="sheet", source_range="A:C")

    assert headers == ["Email", "Name", "Mobile"]
    assert rows == [{"Email": "person@example.com", "Name": "Person"}]
    assert service.spreadsheets().values().request == ("sheet", "A:C")


def test_map_headers_is_case_insensitive_and_maps_canonical_fields() -> None:
    mapped = map_headers(
        ["Email Address", "Full Name"],
        field_mapping={"email": "email address", "name": "full name"},
    )

    assert map_rows(
        [{"Email Address": "person@example.com", "Full Name": "Person"}],
        mapped_headers=mapped,
    ) == [{"email": "person@example.com", "name": "Person"}]


def test_map_headers_requires_email() -> None:
    with pytest.raises(ValueError, match="must include email"):
        map_headers(["Name"], field_mapping={"name": "Name"})
