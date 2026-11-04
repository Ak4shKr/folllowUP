from datetime import time
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import BaseModel


class Campaign(BaseModel):
    __tablename__ = "campaigns"
    __table_args__ = (
        CheckConstraint("email_mode IN ('personalized', 'generic')", name="email_mode_values"),
        CheckConstraint(
            "status IN ('draft', 'active', 'paused', 'completed')", name="status_values"
        ),
        CheckConstraint("daily_limit BETWEEN 1 AND 50", name="daily_limit_range"),
        CheckConstraint("followup_interval_days >= 1", name="followup_interval_days_min"),
        CheckConstraint("max_followups BETWEEN 0 AND 5", name="max_followups_range"),
        CheckConstraint(
            "(sending_window_start IS NULL) = (sending_window_end IS NULL)",
            name="sending_window_pair",
        ),
        Index("ix_campaigns_status", "status"),
        Index("ix_campaigns_job_profile_id", "job_profile_id"),
        {"comment": "Outreach rules and limits for a group of contacts."},
    )

    name: Mapped[str] = mapped_column(Text, nullable=False, comment="Human-readable campaign name.")
    job_profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_profiles.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Profile whose approved facts may be used for drafts.",
    )
    email_mode: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="personalized",
        comment="Whether drafts are personalized or generic.",
    )
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="draft",
        server_default="draft",
        comment="Campaign lifecycle state.",
    )
    daily_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=50,
        server_default="50",
        comment="Maximum accepted sends per local day.",
    )
    followup_interval_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=4,
        server_default="4",
        comment="Days between accepted messages.",
    )
    max_followups: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=2,
        server_default="2",
        comment="Maximum follow-ups per sequence.",
    )
    timezone: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="Asia/Kolkata",
        comment="IANA timezone used for limits and windows.",
    )
    sending_window_start: Mapped[time | None] = mapped_column(
        Time(timezone=False), comment="Local time when sending may begin."
    )
    sending_window_end: Mapped[time | None] = mapped_column(
        Time(timezone=False), comment="Local time when sending must stop."
    )

    job_profile = relationship("JobProfile", back_populates="campaigns")
    enrollments = relationship("CampaignContact", back_populates="campaign")
    messages = relationship("EmailMessage", back_populates="campaign")
    followup_tasks = relationship("FollowupTask", back_populates="campaign")
