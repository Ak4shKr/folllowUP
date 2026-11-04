from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import BaseModel


class FollowupTask(BaseModel):
    __tablename__ = "followup_tasks"
    __table_args__ = (
        UniqueConstraint("previous_email_id", "sequence_number", name="previous_email_sequence"),
        CheckConstraint(
            "status IN ('pending', 'processing', 'completed', 'cancelled', 'failed')",
            name="status_values",
        ),
        CheckConstraint("sequence_number >= 1", name="sequence_positive"),
        CheckConstraint("attempt_count >= 0", name="attempt_count_nonnegative"),
        Index("ix_followup_tasks_status_due", "status", "due_at"),
        Index("ix_followup_tasks_campaign_contact_status", "campaign_contact_id", "status"),
        Index("ix_followup_tasks_contact_status", "contact_id", "status"),
        {"comment": "Pending follow-up work linked to an accepted parent message."},
    )

    contact_id: Mapped[UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Contact to follow up with.",
    )
    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Campaign that schedules the task.",
    )
    campaign_contact_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaign_contacts.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Enrollment being continued.",
    )
    previous_email_id: Mapped[UUID] = mapped_column(
        ForeignKey("email_messages.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Accepted message that the follow-up replies to.",
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Follow-up number within the sequence, starting at one."
    )
    due_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, comment="UTC time when the task becomes due."
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="pending", comment="Task processing state."
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Number of processing attempts.",
    )
    last_error: Mapped[str | None] = mapped_column(
        Text, comment="Safe detail from the last failed attempt."
    )
    skip_reason: Mapped[str | None] = mapped_column(
        Text, comment="Why the task was not sent on a scheduler pass."
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="UTC time when a worker claimed the task."
    )

    contact = relationship("Contact", back_populates="followup_tasks")
    campaign = relationship("Campaign", back_populates="followup_tasks")
    campaign_contact = relationship("CampaignContact", back_populates="followup_tasks")
    previous_email = relationship("EmailMessage", back_populates="followup_tasks")
