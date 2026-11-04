"""create initial schema

Revision ID: 21fb319c6d60
Revises: 
Create Date: 2026-11-05 00:29:17.357736

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '21fb319c6d60'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table('contacts',
    sa.Column('email', sa.Text(), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('company_name', sa.Text(), nullable=True),
    sa.Column('designation', sa.Text(), nullable=True),
    sa.Column('company_website', sa.Text(), nullable=True),
    sa.Column('target_role', sa.Text(), nullable=True),
    sa.Column('source', sa.Text(), nullable=True),
    sa.Column('mobile', sa.Text(), nullable=True),
    sa.Column('status', sa.Text(), server_default='active', nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("email !~ '[[:cntrl:]]'", name=op.f('ck_contacts_email_no_control_chars')),
    sa.CheckConstraint("status IN ('active', 'replied', 'opted_out', 'archived', 'suppressed')", name=op.f('ck_contacts_status_values')),
    sa.CheckConstraint('email = lower(btrim(email))', name=op.f('ck_contacts_email_normalized')),
    sa.CheckConstraint('length(email) BETWEEN 1 AND 254', name=op.f('ck_contacts_email_length')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_contacts')),
    sa.UniqueConstraint('email', name=op.f('uq_contacts_email'))
    )
    op.create_index('ix_contacts_status', 'contacts', ['status'], unique=False)
    op.create_table('import_runs',
    sa.Column('source', sa.Text(), nullable=False),
    sa.Column('sheet_id', sa.Text(), nullable=False),
    sa.Column('range', sa.Text(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('inserted', sa.Integer(), server_default='0', nullable=False),
    sa.Column('updated', sa.Integer(), server_default='0', nullable=False),
    sa.Column('unchanged', sa.Integer(), server_default='0', nullable=False),
    sa.Column('skipped_duplicate', sa.Integer(), server_default='0', nullable=False),
    sa.Column('invalid', sa.Integer(), server_default='0', nullable=False),
    sa.Column('failed', sa.Integer(), server_default='0', nullable=False),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("jsonb_typeof(details) = 'object'", name=op.f('ck_import_runs_details_object')),
    sa.CheckConstraint('failed >= 0', name=op.f('ck_import_runs_failed_nonnegative')),
    sa.CheckConstraint('finished_at IS NULL OR finished_at >= started_at', name=op.f('ck_import_runs_finished_after_started')),
    sa.CheckConstraint('inserted >= 0', name=op.f('ck_import_runs_inserted_nonnegative')),
    sa.CheckConstraint('invalid >= 0', name=op.f('ck_import_runs_invalid_nonnegative')),
    sa.CheckConstraint('skipped_duplicate >= 0', name=op.f('ck_import_runs_skipped_duplicate_nonnegative')),
    sa.CheckConstraint('unchanged >= 0', name=op.f('ck_import_runs_unchanged_nonnegative')),
    sa.CheckConstraint('updated >= 0', name=op.f('ck_import_runs_updated_nonnegative')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_import_runs'))
    )
    op.create_index('ix_import_runs_sheet_range', 'import_runs', ['sheet_id', 'range'], unique=False)
    op.create_index('ix_import_runs_started_at', 'import_runs', ['started_at'], unique=False)
    op.create_table('job_profiles',
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('target_roles', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
    sa.Column('skills', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
    sa.Column('experience_summary', sa.Text(), nullable=True),
    sa.Column('resume_text', sa.Text(), nullable=True),
    sa.Column('resume_reference', sa.Text(), nullable=True),
    sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("jsonb_typeof(skills) = 'array'", name=op.f('ck_job_profiles_skills_array')),
    sa.CheckConstraint("jsonb_typeof(target_roles) = 'array'", name=op.f('ck_job_profiles_target_roles_array')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_job_profiles'))
    )
    op.create_index('ix_job_profiles_is_active', 'job_profiles', ['is_active'], unique=False)
    op.create_table('campaigns',
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('job_profile_id', sa.UUID(), nullable=False),
    sa.Column('email_mode', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default='draft', nullable=False),
    sa.Column('daily_limit', sa.Integer(), server_default='50', nullable=False),
    sa.Column('followup_interval_days', sa.Integer(), server_default='4', nullable=False),
    sa.Column('max_followups', sa.Integer(), server_default='2', nullable=False),
    sa.Column('timezone', sa.Text(), nullable=False),
    sa.Column('sending_window_start', sa.Time(), nullable=True),
    sa.Column('sending_window_end', sa.Time(), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("email_mode IN ('personalized', 'generic')", name=op.f('ck_campaigns_email_mode_values')),
    sa.CheckConstraint("status IN ('draft', 'active', 'paused', 'completed')", name=op.f('ck_campaigns_status_values')),
    sa.CheckConstraint('(sending_window_start IS NULL) = (sending_window_end IS NULL)', name=op.f('ck_campaigns_sending_window_pair')),
    sa.CheckConstraint('daily_limit BETWEEN 1 AND 50', name=op.f('ck_campaigns_daily_limit_range')),
    sa.CheckConstraint('followup_interval_days >= 1', name=op.f('ck_campaigns_followup_interval_days_min')),
    sa.CheckConstraint('max_followups BETWEEN 0 AND 5', name=op.f('ck_campaigns_max_followups_range')),
    sa.ForeignKeyConstraint(['job_profile_id'], ['job_profiles.id'], name=op.f('fk_campaigns_job_profile_id_job_profiles'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_campaigns'))
    )
    op.create_index('ix_campaigns_job_profile_id', 'campaigns', ['job_profile_id'], unique=False)
    op.create_index('ix_campaigns_status', 'campaigns', ['status'], unique=False)
    op.create_table('campaign_contacts',
    sa.Column('campaign_id', sa.UUID(), nullable=False),
    sa.Column('contact_id', sa.UUID(), nullable=False),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('stopped_reason', sa.Text(), nullable=True),
    sa.Column('sequence_base', sa.Integer(), server_default='0', nullable=False),
    sa.Column('enrolled_at', sa.DateTime(timezone=True), server_default='now()', nullable=False),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status != 'stopped' OR stopped_reason IS NOT NULL", name=op.f('ck_campaign_contacts_stopped_reason')),
    sa.CheckConstraint("status IN ('enrolled', 'active', 'completed', 'stopped')", name=op.f('ck_campaign_contacts_status_values')),
    sa.CheckConstraint('sequence_base >= 0', name=op.f('ck_campaign_contacts_sequence_base_nonnegative')),
    sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], name=op.f('fk_campaign_contacts_campaign_id_campaigns'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], name=op.f('fk_campaign_contacts_contact_id_contacts'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_campaign_contacts')),
    sa.UniqueConstraint('campaign_id', 'contact_id', name='campaign_contact_pair')
    )
    op.create_index('ix_campaign_contacts_campaign_status', 'campaign_contacts', ['campaign_id', 'status'], unique=False)
    op.create_index('ix_campaign_contacts_contact_id', 'campaign_contacts', ['contact_id'], unique=False)
    op.create_table('email_messages',
    sa.Column('contact_id', sa.UUID(), nullable=False),
    sa.Column('campaign_id', sa.UUID(), nullable=False),
    sa.Column('campaign_contact_id', sa.UUID(), nullable=False),
    sa.Column('parent_email_id', sa.UUID(), nullable=True),
    sa.Column('email_type', sa.Text(), nullable=False),
    sa.Column('sequence_number', sa.Integer(), nullable=False),
    sa.Column('subject', sa.Text(), nullable=False),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('provider_message_id', sa.Text(), nullable=True),
    sa.Column('provider_thread_id', sa.Text(), nullable=True),
    sa.Column('message_id_header', sa.Text(), nullable=False),
    sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('error_code', sa.Text(), nullable=True),
    sa.Column('error_message', sa.Text(), nullable=True),
    sa.Column('skip_reason', sa.Text(), nullable=True),
    sa.Column('prompt_version', sa.Text(), nullable=True),
    sa.Column('model_name', sa.Text(), nullable=True),
    sa.Column('input_fingerprint', sa.Text(), nullable=True),
    sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("(email_type = 'initial' AND sequence_number = 0 AND parent_email_id IS NULL) OR (email_type = 'followup' AND sequence_number >= 1 AND parent_email_id IS NOT NULL)", name=op.f('ck_email_messages_type_sequence_parent')),
    sa.CheckConstraint("email_type IN ('initial', 'followup')", name=op.f('ck_email_messages_email_type_values')),
    sa.CheckConstraint("status IN ('draft', 'pending_approval', 'approved', 'scheduled', 'sending', 'sent', 'failed', 'unknown_outcome', 'cancelled')", name=op.f('ck_email_messages_status_values')),
    sa.CheckConstraint('attempt_count >= 0', name=op.f('ck_email_messages_attempt_count_nonnegative')),
    sa.CheckConstraint('char_length(body) BETWEEN 1 AND 4000', name=op.f('ck_email_messages_body_length')),
    sa.CheckConstraint('char_length(subject) BETWEEN 1 AND 150', name=op.f('ck_email_messages_subject_length')),
    sa.CheckConstraint('sequence_number >= 0', name=op.f('ck_email_messages_sequence_nonnegative')),
    sa.ForeignKeyConstraint(['campaign_contact_id'], ['campaign_contacts.id'], name=op.f('fk_email_messages_campaign_contact_id_campaign_contacts'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], name=op.f('fk_email_messages_campaign_id_campaigns'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], name=op.f('fk_email_messages_contact_id_contacts'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['parent_email_id'], ['email_messages.id'], name=op.f('fk_email_messages_parent_email_id_email_messages'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_email_messages')),
    sa.UniqueConstraint('campaign_contact_id', 'email_type', 'sequence_number', name='message_sequence'),
    sa.UniqueConstraint('message_id_header', name=op.f('uq_email_messages_message_id_header'))
    )
    op.create_index('ix_email_messages_campaign_contact', 'email_messages', ['campaign_contact_id'], unique=False)
    op.create_index('ix_email_messages_campaign_status', 'email_messages', ['campaign_id', 'status'], unique=False)
    op.create_index('ix_email_messages_contact_id', 'email_messages', ['contact_id'], unique=False)
    op.create_index('ix_email_messages_provider_thread', 'email_messages', ['provider_thread_id'], unique=False)
    op.create_index('ix_email_messages_status_scheduled', 'email_messages', ['status', 'scheduled_at'], unique=False)
    op.create_table('followup_tasks',
    sa.Column('contact_id', sa.UUID(), nullable=False),
    sa.Column('campaign_id', sa.UUID(), nullable=False),
    sa.Column('campaign_contact_id', sa.UUID(), nullable=False),
    sa.Column('previous_email_id', sa.UUID(), nullable=False),
    sa.Column('sequence_number', sa.Integer(), nullable=False),
    sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('status', sa.Text(), nullable=False),
    sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('last_error', sa.Text(), nullable=True),
    sa.Column('skip_reason', sa.Text(), nullable=True),
    sa.Column('claimed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.UUID(), server_default=sa.text('gen_random_uuid()'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('pending', 'processing', 'completed', 'cancelled', 'failed')", name=op.f('ck_followup_tasks_status_values')),
    sa.CheckConstraint('attempt_count >= 0', name=op.f('ck_followup_tasks_attempt_count_nonnegative')),
    sa.CheckConstraint('sequence_number >= 1', name=op.f('ck_followup_tasks_sequence_positive')),
    sa.ForeignKeyConstraint(['campaign_contact_id'], ['campaign_contacts.id'], name=op.f('fk_followup_tasks_campaign_contact_id_campaign_contacts'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['campaign_id'], ['campaigns.id'], name=op.f('fk_followup_tasks_campaign_id_campaigns'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['contact_id'], ['contacts.id'], name=op.f('fk_followup_tasks_contact_id_contacts'), ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['previous_email_id'], ['email_messages.id'], name=op.f('fk_followup_tasks_previous_email_id_email_messages'), ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_followup_tasks')),
    sa.UniqueConstraint('previous_email_id', 'sequence_number', name='previous_email_sequence')
    )
    op.create_index('ix_followup_tasks_campaign_contact_status', 'followup_tasks', ['campaign_contact_id', 'status'], unique=False)
    op.create_index('ix_followup_tasks_contact_status', 'followup_tasks', ['contact_id', 'status'], unique=False)
    op.create_index('ix_followup_tasks_status_due', 'followup_tasks', ['status', 'due_at'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_followup_tasks_status_due', table_name='followup_tasks')
    op.drop_index('ix_followup_tasks_contact_status', table_name='followup_tasks')
    op.drop_index('ix_followup_tasks_campaign_contact_status', table_name='followup_tasks')
    op.drop_table('followup_tasks')
    op.drop_index('ix_email_messages_status_scheduled', table_name='email_messages')
    op.drop_index('ix_email_messages_provider_thread', table_name='email_messages')
    op.drop_index('ix_email_messages_contact_id', table_name='email_messages')
    op.drop_index('ix_email_messages_campaign_status', table_name='email_messages')
    op.drop_index('ix_email_messages_campaign_contact', table_name='email_messages')
    op.drop_table('email_messages')
    op.drop_index('ix_campaign_contacts_contact_id', table_name='campaign_contacts')
    op.drop_index('ix_campaign_contacts_campaign_status', table_name='campaign_contacts')
    op.drop_table('campaign_contacts')
    op.drop_index('ix_campaigns_status', table_name='campaigns')
    op.drop_index('ix_campaigns_job_profile_id', table_name='campaigns')
    op.drop_table('campaigns')
    op.drop_index('ix_job_profiles_is_active', table_name='job_profiles')
    op.drop_table('job_profiles')
    op.drop_index('ix_import_runs_started_at', table_name='import_runs')
    op.drop_index('ix_import_runs_sheet_range', table_name='import_runs')
    op.drop_table('import_runs')
    op.drop_index('ix_contacts_status', table_name='contacts')
    op.drop_table('contacts')
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
    # ### end Alembic commands ###
