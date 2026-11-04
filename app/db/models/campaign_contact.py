from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import BaseModel


class CampaignContact(BaseModel):
    __tablename__ = "campaign_contacts"
    __table_args__ = (
        UniqueConstraint("campaign_id", "contact_id", name="campaign_contact_pair"),
        CheckConstraint(
            "status IN ('enrolled', 'active', 'completed', 'stopped')", name="status_values"
        ),
        CheckConstraint("sequence_base >= 0", name="sequence_base_nonnegative"),
        CheckConstraint("status != 'stopped' OR stopped_reason IS NOT NULL", name="stopped_reason"),
        Index("ix_campaign_contacts_campaign_status", "campaign_id", "status"),
        Index("ix_campaign_contacts_contact_id", "contact_id"),
        {"comment": "A contact's progress within one campaign."},
    )

    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Campaign that owns this enrollment.",
    )
    contact_id: Mapped[UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Contact enrolled in the campaign.",
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="enrolled", comment="Enrollment lifecycle state."
    )
    stopped_reason: Mapped[str | None] = mapped_column(
        Text, comment="Reason recorded when outreach for this enrollment stops."
    )
    sequence_base: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="Sequence offset used when a completed enrollment is started again.",
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default="now()",
        comment="Time of enrollment.",
    )

    campaign = relationship("Campaign", back_populates="enrollments")
    contact = relationship("Contact", back_populates="enrollments")
    messages = relationship("EmailMessage", back_populates="campaign_contact")
    followup_tasks = relationship("FollowupTask", back_populates="campaign_contact")
