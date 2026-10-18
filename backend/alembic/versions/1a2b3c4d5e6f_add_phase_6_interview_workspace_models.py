"""Add Phase 6 interview and scheduling workspace models

Revision ID: 1a2b3c4d5e6f
Revises: f6a7b8c9d0e1
Create Date: 2026-10-16 16:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db.guid


# revision identifiers, used by Alembic.
revision: str = '1a2b3c4d5e6f'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

interview_mode_enum = sa.Enum(
    'ONLINE', 'IN_PERSON', 'PHONE',
    name='interviewmodetype',
)

interview_status_enum = sa.Enum(
    'DRAFT', 'SCHEDULED', 'CONFIRMED', 'COMPLETED', 'CANCELLED', 'RESCHEDULED',
    name='interviewstatustype',
)

interview_round_enum = sa.Enum(
    'SCREENING', 'TECHNICAL', 'SYSTEM_DESIGN', 'BEHAVIORAL', 'MANAGERIAL', 'CULTURE_FIT', 'EXECUTIVE', 'FINAL', 'OTHER',
    name='interviewroundtype',
)

participant_role_enum = sa.Enum(
    'INTERVIEWER', 'RECRUITER', 'OBSERVER',
    name='participantroletype',
)

attendance_status_enum = sa.Enum(
    'INVITED', 'ACCEPTED', 'DECLINED', 'ATTENDED', 'NO_SHOW',
    name='attendancestatustype',
)

feedback_rec_enum = sa.Enum(
    'STRONG_YES', 'YES', 'MAYBE', 'NO', 'STRONG_NO',
    name='feedbackrecommendationtype',
)


def upgrade() -> None:
    # 1. Create interviews table
    op.create_table(
        'interviews',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('application_id', app.db.guid.GUID(), nullable=False),
        sa.Column('round_name', sa.String(length=100), nullable=False),
        sa.Column('round_type', interview_round_enum, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('interview_mode', interview_mode_enum, nullable=False),
        sa.Column('scheduled_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scheduled_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('timezone', sa.String(length=50), nullable=False, server_default='Asia/Kolkata'),
        sa.Column('location', sa.String(length=255), nullable=True),
        sa.Column('meeting_url', sa.String(length=500), nullable=True),
        sa.Column('status', interview_status_enum, nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_by', app.db.guid.GUID(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_interviews_agency_id'), 'interviews', ['agency_id'], unique=False)
    op.create_index(op.f('ix_interviews_application_id'), 'interviews', ['application_id'], unique=False)
    op.create_index(op.f('ix_interviews_round_type'), 'interviews', ['round_type'], unique=False)
    op.create_index(op.f('ix_interviews_scheduled_start'), 'interviews', ['scheduled_start'], unique=False)
    op.create_index(op.f('ix_interviews_scheduled_end'), 'interviews', ['scheduled_end'], unique=False)
    op.create_index(op.f('ix_interviews_status'), 'interviews', ['status'], unique=False)
    op.create_index(op.f('ix_interviews_created_by'), 'interviews', ['created_by'], unique=False)
    op.create_index('ix_interviews_agency_app', 'interviews', ['agency_id', 'application_id'], unique=False)
    op.create_index('ix_interviews_agency_status', 'interviews', ['agency_id', 'status'], unique=False)
    op.create_index('ix_interviews_agency_start', 'interviews', ['agency_id', 'scheduled_start'], unique=False)
    op.create_index('ix_interviews_agency_app_status', 'interviews', ['agency_id', 'application_id', 'status'], unique=False)

    # 2. Create interview_participants table
    op.create_table(
        'interview_participants',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('interview_id', app.db.guid.GUID(), nullable=False),
        sa.Column('user_id', app.db.guid.GUID(), nullable=True),
        sa.Column('participant_name', sa.String(length=150), nullable=False),
        sa.Column('participant_email', sa.String(length=255), nullable=False),
        sa.Column('participant_role', participant_role_enum, nullable=False),
        sa.Column('attendance_status', attendance_status_enum, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_interview_participants_agency_id'), 'interview_participants', ['agency_id'], unique=False)
    op.create_index(op.f('ix_interview_participants_interview_id'), 'interview_participants', ['interview_id'], unique=False)
    op.create_index(op.f('ix_interview_participants_user_id'), 'interview_participants', ['user_id'], unique=False)
    op.create_index('ix_participants_interview_email', 'interview_participants', ['interview_id', 'participant_email'], unique=False)
    op.create_index('ix_participants_interview_user', 'interview_participants', ['interview_id', 'user_id'], unique=False)

    # 3. Create interview_feedbacks table
    op.create_table(
        'interview_feedbacks',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('interview_id', app.db.guid.GUID(), nullable=False),
        sa.Column('reviewer_id', app.db.guid.GUID(), nullable=False),
        sa.Column('overall_rating', sa.Integer(), nullable=False),
        sa.Column('recommendation', feedback_rec_enum, nullable=False),
        sa.Column('technical_assessment', sa.Text(), nullable=True),
        sa.Column('communication_assessment', sa.Text(), nullable=True),
        sa.Column('problem_solving_assessment', sa.Text(), nullable=True),
        sa.Column('role_specific_assessment', sa.Text(), nullable=True),
        sa.Column('strengths', sa.Text(), nullable=True),
        sa.Column('concerns', sa.Text(), nullable=True),
        sa.Column('detailed_feedback', sa.Text(), nullable=False),
        sa.Column('is_private', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['reviewer_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('interview_id', 'reviewer_id', name='uq_interview_reviewer_feedback'),
    )
    op.create_index(op.f('ix_interview_feedbacks_agency_id'), 'interview_feedbacks', ['agency_id'], unique=False)
    op.create_index(op.f('ix_interview_feedbacks_interview_id'), 'interview_feedbacks', ['interview_id'], unique=False)
    op.create_index(op.f('ix_interview_feedbacks_reviewer_id'), 'interview_feedbacks', ['reviewer_id'], unique=False)
    op.create_index('ix_interview_feedbacks_interview', 'interview_feedbacks', ['interview_id'], unique=False)

    # 4. Create interview_histories table
    op.create_table(
        'interview_histories',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('interview_id', app.db.guid.GUID(), nullable=False),
        sa.Column('actor_id', app.db.guid.GUID(), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('previous_value', sa.Text(), nullable=True),
        sa.Column('new_value', sa.Text(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actor_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_interview_histories_agency_id'), 'interview_histories', ['agency_id'], unique=False)
    op.create_index(op.f('ix_interview_histories_interview_id'), 'interview_histories', ['interview_id'], unique=False)
    op.create_index(op.f('ix_interview_histories_actor_id'), 'interview_histories', ['actor_id'], unique=False)
    op.create_index('ix_interview_histories_interview_created', 'interview_histories', ['interview_id', 'created_at'], unique=False)


def downgrade() -> None:
    op.drop_table('interview_histories')
    op.drop_table('interview_feedbacks')
    op.drop_table('interview_participants')
    op.drop_table('interviews')
