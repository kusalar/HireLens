"""Add Phase 5 recruitment workspace and application pipeline models

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-10-16 08:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db.guid


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

pipeline_stage_enum = sa.Enum(
    'APPLIED',
    'UNDER_REVIEW',
    'SHORTLISTED',
    'INTERVIEW',
    'SELECTED',
    'REJECTED',
    'ON_HOLD',
    'WITHDRAWN',
    name='pipelinestagetype',
)


def upgrade() -> None:
    # 1. Create applications table
    op.create_table(
        'applications',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('job_id', app.db.guid.GUID(), nullable=False),
        sa.Column('candidate_id', app.db.guid.GUID(), nullable=False),
        sa.Column('status', pipeline_stage_enum, nullable=False),
        sa.Column('source', sa.String(length=100), nullable=True),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('shortlisted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('assigned_recruiter_id', app.db.guid.GUID(), nullable=True),
        sa.Column('recruiter_summary', sa.Text(), nullable=True),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_recruiter_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_applications_agency_id'), 'applications', ['agency_id'], unique=False)
    op.create_index(op.f('ix_applications_job_id'), 'applications', ['job_id'], unique=False)
    op.create_index(op.f('ix_applications_candidate_id'), 'applications', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_applications_status'), 'applications', ['status'], unique=False)
    op.create_index(op.f('ix_applications_assigned_recruiter_id'), 'applications', ['assigned_recruiter_id'], unique=False)
    op.create_index('ix_applications_agency_job', 'applications', ['agency_id', 'job_id'], unique=False)
    op.create_index('ix_applications_agency_candidate', 'applications', ['agency_id', 'candidate_id'], unique=False)
    op.create_index('ix_applications_agency_job_candidate', 'applications', ['agency_id', 'job_id', 'candidate_id'], unique=False)
    op.create_index('ix_applications_agency_status', 'applications', ['agency_id', 'status'], unique=False)
    op.create_index('ix_applications_agency_recruiter', 'applications', ['agency_id', 'assigned_recruiter_id'], unique=False)

    # 2. Create application_stage_histories table
    op.create_table(
        'application_stage_histories',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('application_id', app.db.guid.GUID(), nullable=False),
        sa.Column('previous_stage', pipeline_stage_enum, nullable=True),
        sa.Column('new_stage', pipeline_stage_enum, nullable=False),
        sa.Column('changed_by', app.db.guid.GUID(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_application_stage_histories_agency_id'), 'application_stage_histories', ['agency_id'], unique=False)
    op.create_index(op.f('ix_application_stage_histories_application_id'), 'application_stage_histories', ['application_id'], unique=False)
    op.create_index(op.f('ix_application_stage_histories_changed_by'), 'application_stage_histories', ['changed_by'], unique=False)
    op.create_index('ix_stage_histories_app_created', 'application_stage_histories', ['application_id', 'created_at'], unique=False)

    # 3. Create application_notes table
    op.create_table(
        'application_notes',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('application_id', app.db.guid.GUID(), nullable=False),
        sa.Column('author_id', app.db.guid.GUID(), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_application_notes_agency_id'), 'application_notes', ['agency_id'], unique=False)
    op.create_index(op.f('ix_application_notes_application_id'), 'application_notes', ['application_id'], unique=False)
    op.create_index(op.f('ix_application_notes_author_id'), 'application_notes', ['author_id'], unique=False)
    op.create_index('ix_application_notes_app_created', 'application_notes', ['application_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('application_notes')
    op.drop_table('application_stage_histories')
    op.drop_table('applications')
