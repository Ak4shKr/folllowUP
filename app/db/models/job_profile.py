from sqlalchemy import Boolean, CheckConstraint, Index, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.models.base import BaseModel


class JobProfile(BaseModel):
    __tablename__ = "job_profiles"
    __table_args__ = (
        CheckConstraint("jsonb_typeof(target_roles) = 'array'", name="target_roles_array"),
        CheckConstraint("jsonb_typeof(skills) = 'array'", name="skills_array"),
        Index("ix_job_profiles_is_active", "is_active"),
        {"comment": "Sender facts used to ground future email drafts."},
    )

    name: Mapped[str] = mapped_column(Text, nullable=False, comment="Human-readable profile name.")
    target_roles: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default="[]", comment="Target roles for this profile."
    )
    skills: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, server_default="[]", comment="Skills that may be used in drafts."
    )
    experience_summary: Mapped[str | None] = mapped_column(
        Text, comment="Approved experience facts for draft generation."
    )
    resume_text: Mapped[str | None] = mapped_column(Text, comment="Stored resume text, when used.")
    resume_reference: Mapped[str | None] = mapped_column(
        Text, comment="Reference to a resume stored outside the database."
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
        comment="Whether this profile can be used for new drafts.",
    )

    campaigns = relationship("Campaign", back_populates="job_profile")
