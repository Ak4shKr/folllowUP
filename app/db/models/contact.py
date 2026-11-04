from sqlalchemy import CheckConstraint, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import BaseModel


class Contact(BaseModel):
    __tablename__ = "contacts"
    __table_args__ = (
        CheckConstraint("email = lower(btrim(email))", name="email_normalized"),
        CheckConstraint("length(email) BETWEEN 1 AND 254", name="email_length"),
        CheckConstraint("email !~ '[[:cntrl:]]'", name="email_no_control_chars"),
        CheckConstraint(
            "status IN ('active', 'replied', 'opted_out', 'archived', 'suppressed')",
            name="status_values",
        ),
        Index("ix_contacts_status", "status"),
        {"comment": "People imported for job outreach."},
    )

    email: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        comment="Normalized contact email used as the identity key.",
    )
    name: Mapped[str | None] = mapped_column(Text, comment="Contact name from the import source.")
    company_name: Mapped[str | None] = mapped_column(
        Text, comment="Contact company name from the source."
    )
    designation: Mapped[str | None] = mapped_column(
        Text, comment="Contact job title from the source."
    )
    company_website: Mapped[str | None] = mapped_column(
        Text, comment="Company website from the source."
    )
    target_role: Mapped[str | None] = mapped_column(
        Text, comment="Role this contact is associated with."
    )
    source: Mapped[str | None] = mapped_column(
        Text, comment="Source that provided the contact row."
    )
    mobile: Mapped[str | None] = mapped_column(
        Text, comment="Optional source-owned mobile value stored as text; no SMS behavior."
    )
    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="active",
        server_default="active",
        comment="System-managed state that controls whether outreach is allowed.",
    )

    enrollments = relationship("CampaignContact", back_populates="contact")
    messages = relationship("EmailMessage", back_populates="contact")
    followup_tasks = relationship("FollowupTask", back_populates="contact")
