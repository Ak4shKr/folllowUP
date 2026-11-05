import argparse
import asyncio
import json
from pathlib import Path

from app.core.env import env
from app.db.session import SessionLocal, engine
from app.integrations.google_sheets import (
    build_sheets_service,
    fetch_rows,
    load_service_account_credentials,
    map_headers,
    map_rows,
)
from app.services.contact_import import import_contacts


def parse_field_mapping(value: str) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in value.split(","):
        field, separator, header = item.partition("=")
        if not separator or not field.strip() or not header.strip():
            raise ValueError(f"Invalid field mapping item: {item!r}")
        mapping[field.strip()] = header.strip()
    return mapping


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    commands = parser.add_subparsers(dest="command", required=True)
    import_parser = commands.add_parser("import")
    import_parser.add_argument("--dry-run", action="store_true")
    return parser


async def run_import(*, dry_run: bool) -> None:
    if not env.google_sheet_id or not env.google_credentials_file:
        raise ValueError("GOOGLE_SHEET_ID and GOOGLE_CREDENTIALS_FILE are required")

    credentials_path = Path(env.google_credentials_file)
    if not await asyncio.to_thread(credentials_path.is_file):
        raise ValueError(f"Google credentials file was not found: {credentials_path}")

    credentials = load_service_account_credentials(credentials_path)
    service = build_sheets_service(credentials)
    headers, raw_rows = await asyncio.to_thread(
        fetch_rows,
        service,
        spreadsheet_id=env.google_sheet_id,
        source_range=env.google_sheet_range,
    )
    mapped_headers = map_headers(
        headers, field_mapping=parse_field_mapping(env.google_field_mapping)
    )
    rows = map_rows(raw_rows, mapped_headers=mapped_headers)
    row_numbers = list(range(2, len(rows) + 2))

    async with SessionLocal() as session:
        summary = await import_contacts(
            session,
            rows,
            source="google_sheets",
            sheet_id=env.google_sheet_id,
            source_range=env.google_sheet_range,
            row_numbers=row_numbers,
            dry_run=dry_run,
        )
    print(json.dumps(summary.__dict__, default=str))


async def async_main() -> None:
    args = build_parser().parse_args()
    if args.command == "import":
        await run_import(dry_run=args.dry_run)
    await engine.dispose()


def main() -> None:
    asyncio.run(async_main())


if __name__ == "__main__":
    main()
