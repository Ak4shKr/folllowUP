from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import BaseModel


class EmailMessage(BaseModel):
    __tablename__ = "email_messages"
    __table_args__ = (
        UniqueConstraint(
            "campaign_contact_id",
            "email_type",
            "sequence_number",
            name="message_sequence",
        ),
        CheckConstraint(
            "status IN ('draft', 'pending_approval', 'approved', 'scheduled', 'sending', 'sent', 'failed', 'unknown_outcome', 'cancelled')",
            name="status_values",
        ),
        CheckConstraint("email_type IN ('initial', 'followup')", name="email_type_values"),
        CheckConstraint("sequence_number >= 0", name="sequence_nonnegative"),
        CheckConstraint(
            "(email_type = 'initial' AND sequence_number = 0 AND parent_email_id IS NULL) OR "
            "(email_type = 'followup' AND sequence_number >= 1 AND parent_email_id IS NOT NULL)",
            name="type_sequence_parent",
        ),
        CheckConstraint("attempt_count >= 0", name="attempt_count_nonnegative"),
        CheckConstraint("char_length(subject) BETWEEN 1 AND 150", name="subject_length"),
        CheckConstraint("char_length(body) BETWEEN 1 AND 4000", name="body_length"),
        Index("ix_email_messages_status_scheduled", "status", "scheduled_at"),
        Index("ix_email_messages_contact_id", "contact_id"),
        Index("ix_email_messages_campaign_status", "campaign_id", "status"),
        Index("ix_email_messages_campaign_contact", "campaign_contact_id"),
        Index("ix_email_messages_provider_thread", "provider_thread_id"),
        {"comment": "Email drafts and send history for a campaign sequence."},
    )

    contact_id: Mapped[UUID] = mapped_column(
        ForeignKey("contacts.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Contact who receives this message.",
    )
    campaign_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaigns.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Campaign that owns this message.",
    )
    campaign_contact_id: Mapped[UUID] = mapped_column(
        ForeignKey("campaign_contacts.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Enrollment that produced this message.",
    )
    parent_email_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("email_messages.id", ondelete="RESTRICT"),
        comment="Previous message in the same thread for a follow-up.",
    )
    email_type: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Initial message or follow-up message."
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Zero for the initial message; one or more for follow-ups."
    )
    subject: Mapped[str] = mapped_column(Text, nullable=False, comment="Email subject.")
    body: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Email body awaiting or after approval."
    )
    status: Mapped[str] = mapped_column(
        Text, nullable=False, default="draft", comment="Draft and delivery lifecycle state."
    )
    scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="UTC time when this message may be sent."
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="UTC time when the provider accepted the message."
    )
    provider_message_id: Mapped[str | None] = mapped_column(
        Text, comment="Message identifier returned by the email provider."
    )
    provider_thread_id: Mapped[str | None] = mapped_column(
        Text, comment="Provider thread identifier used for replies and follow-ups."
    )
    message_id_header: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        comment="Deterministic header used to prevent duplicates and reconcile uncertain sends.",
    )
    attempt_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0", comment="Number of send attempts."
    )
    error_code: Mapped[str | None] = mapped_column(
        Text, comment="Safe provider or application error code."
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, comment="Safe failure detail for operators."
    )
    skip_reason: Mapped[str | None] = mapped_column(
        Text, comment="Last reason the eligibility check blocked sending."
    )
    prompt_version: Mapped[str | None] = mapped_column(
        Text, comment="Prompt version used to create the draft."
    )
    model_name: Mapped[str | None] = mapped_column(Text, comment="Model used to create the draft.")
    input_fingerprint: Mapped[str | None] = mapped_column(
        Text, comment="Hash of facts used to create the draft."
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="UTC time when a person approved the message."
    )

    contact = relationship("Contact", back_populates="messages")
    campaign = relationship("Campaign", back_populates="messages")
    campaign_contact = relationship("CampaignContact", back_populates="messages")
    parent = relationship("EmailMessage", remote_side="EmailMessage.id")
    followup_tasks = relationship("FollowupTask", back_populates="previous_email")
