from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.models.base import BaseModel


class ImportRun(BaseModel):
    __tablename__ = "import_runs"
    __table_args__ = (
        CheckConstraint("inserted >= 0", name="inserted_nonnegative"),
        CheckConstraint("updated >= 0", name="updated_nonnegative"),
        CheckConstraint("unchanged >= 0", name="unchanged_nonnegative"),
        CheckConstraint("skipped_duplicate >= 0", name="skipped_duplicate_nonnegative"),
        CheckConstraint("invalid >= 0", name="invalid_nonnegative"),
        CheckConstraint("failed >= 0", name="failed_nonnegative"),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at", name="finished_after_started"
        ),
        CheckConstraint("jsonb_typeof(details) = 'object'", name="details_object"),
        Index("ix_import_runs_started_at", "started_at"),
        Index("ix_import_runs_sheet_range", "sheet_id", "range"),
        {"comment": "Summary of one contact import attempt."},
    )

    source: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Import provider or source name."
    )
    sheet_id: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Source spreadsheet identifier."
    )
    range: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Source range read during the import."
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="UTC time when the import started."
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="UTC time when the import finished."
    )
    inserted: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Rows inserted as new contacts.",
    )
    updated: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Existing contacts with source fields updated.",
    )
    unchanged: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Valid rows that changed nothing.",
    )
    skipped_duplicate: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Duplicate rows skipped within the import.",
    )
    invalid: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Rows rejected with validation errors.",
    )
    failed: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Rows that failed during database processing.",
    )
    details: Mapped[dict[str, object]] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        comment="Redacted row numbers and validation reasons.",
    )
