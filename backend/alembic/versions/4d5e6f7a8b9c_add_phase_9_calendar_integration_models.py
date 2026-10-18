"""Add Phase 9 calendar integration models

Revision ID: 4d5e6f7a8b9c
Revises: 3c4d5e6f7a8b
Create Date: 2026-10-17 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db.guid


# revision identifiers, used by Alembic.
revision: str = '4d5e6f7a8b9c'
down_revision: Union[str, Sequence[str], None] = '3c4d5e6f7a8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

calendar_provider_enum = sa.Enum(
    'GOOGLE',
    'MICROSOFT',
    'MOCK',
    name='calendarprovidertype',
)

calendar_sync_status_enum = sa.Enum(
    'SYNCED',
    'PENDING',
    'FAILED',
    'CANCELLED',
    name='calendarsyncstatus',
)

calendar_sync_direction_enum = sa.Enum(
    'OUTBOUND',
    'INBOUND',
    name='calendarsyncdirection',
)

calendar_sync_operation_enum = sa.Enum(
    'CREATE',
    'UPDATE',
    'CANCEL',
    'RESYNC',
    name='calendarsyncoperation',
)

meeting_provider_enum = sa.Enum(
    'GOOGLE_MEET',
    'MS_TEAMS',
    'NONE',
    name='meetingprovidertype',
)


def upgrade() -> None:
    # 1. calendar_connections
    op.create_table(
        'calendar_connections',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('user_id', app.db.guid.GUID(), nullable=False),
        sa.Column('provider', calendar_provider_enum, nullable=False),
        sa.Column('provider_account_id', sa.String(length=255), nullable=True),
        sa.Column('provider_account_email', sa.String(length=255), nullable=True),
        sa.Column('encrypted_access_token', sa.Text(), nullable=True),
        sa.Column('encrypted_refresh_token', sa.Text(), nullable=True),
        sa.Column('access_token_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('selected_calendar_id', sa.String(length=255), server_default='primary', nullable=False),
        sa.Column('selected_calendar_name', sa.String(length=255), server_default='Primary Calendar', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agency_id', 'user_id', 'provider', name='uq_calendar_connections_agency_user_provider'),
    )
    op.create_index('ix_calendar_connections_agency_id', 'calendar_connections', ['agency_id'])
    op.create_index('ix_calendar_connections_user_id', 'calendar_connections', ['user_id'])
    op.create_index('ix_calendar_connections_provider', 'calendar_connections', ['provider'])
    op.create_index('ix_calendar_connections_agency_active', 'calendar_connections', ['agency_id', 'is_active'])

    # 2. calendar_event_mappings
    op.create_table(
        'calendar_event_mappings',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('connection_id', app.db.guid.GUID(), nullable=False),
        sa.Column('interview_id', app.db.guid.GUID(), nullable=False),
        sa.Column('external_event_id', sa.String(length=255), nullable=False),
        sa.Column('external_calendar_id', sa.String(length=255), server_default='primary', nullable=False),
        sa.Column('provider', calendar_provider_enum, nullable=False),
        sa.Column('meeting_link', sa.String(length=1024), nullable=True),
        sa.Column('meeting_provider', meeting_provider_enum, server_default='NONE', nullable=False),
        sa.Column('sync_status', calendar_sync_status_enum, server_default='SYNCED', nullable=False),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['connection_id'], ['calendar_connections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agency_id', 'interview_id', 'connection_id', name='uq_calendar_event_mappings_agency_interview_conn'),
        sa.UniqueConstraint('connection_id', 'external_event_id', name='uq_calendar_event_mappings_conn_external_event'),
    )
    op.create_index('ix_calendar_event_mappings_agency_id', 'calendar_event_mappings', ['agency_id'])
    op.create_index('ix_calendar_event_mappings_connection_id', 'calendar_event_mappings', ['connection_id'])
    op.create_index('ix_calendar_event_mappings_interview_id', 'calendar_event_mappings', ['interview_id'])
    op.create_index('ix_calendar_event_mappings_external_event_id', 'calendar_event_mappings', ['external_event_id'])
    op.create_index('ix_calendar_event_mappings_sync_status', 'calendar_event_mappings', ['sync_status'])
    op.create_index('ix_calendar_event_mappings_agency_status', 'calendar_event_mappings', ['agency_id', 'sync_status'])

    # 3. calendar_sync_jobs (Durable Outbox)
    op.create_table(
        'calendar_sync_jobs',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('connection_id', app.db.guid.GUID(), nullable=False),
        sa.Column('interview_id', app.db.guid.GUID(), nullable=False),
        sa.Column('operation', calendar_sync_operation_enum, nullable=False),
        sa.Column('status', sa.String(length=32), server_default='PENDING', nullable=False),
        sa.Column('attempt_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('max_attempts', sa.Integer(), server_default='5', nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('payload', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['connection_id'], ['calendar_connections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['interview_id'], ['interviews.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key', name='uq_calendar_sync_jobs_idempotency_key'),
    )
    op.create_index('ix_calendar_sync_jobs_agency_id', 'calendar_sync_jobs', ['agency_id'])
    op.create_index('ix_calendar_sync_jobs_connection_id', 'calendar_sync_jobs', ['connection_id'])
    op.create_index('ix_calendar_sync_jobs_interview_id', 'calendar_sync_jobs', ['interview_id'])
    op.create_index('ix_calendar_sync_jobs_status', 'calendar_sync_jobs', ['status'])
    op.create_index('ix_calendar_sync_jobs_scheduled_at', 'calendar_sync_jobs', ['scheduled_at'])
    op.create_index('ix_calendar_sync_jobs_idempotency_key', 'calendar_sync_jobs', ['idempotency_key'])
    op.create_index('ix_calendar_sync_jobs_agency_status_scheduled', 'calendar_sync_jobs', ['agency_id', 'status', 'scheduled_at'])

    # 4. calendar_sync_logs
    op.create_table(
        'calendar_sync_logs',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('connection_id', app.db.guid.GUID(), nullable=True),
        sa.Column('interview_id', app.db.guid.GUID(), nullable=True),
        sa.Column('direction', calendar_sync_direction_enum, nullable=False),
        sa.Column('operation', calendar_sync_operation_enum, nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_calendar_sync_logs_agency_id', 'calendar_sync_logs', ['agency_id'])
    op.create_index('ix_calendar_sync_logs_connection_id', 'calendar_sync_logs', ['connection_id'])
    op.create_index('ix_calendar_sync_logs_interview_id', 'calendar_sync_logs', ['interview_id'])
    op.create_index('ix_calendar_sync_logs_status', 'calendar_sync_logs', ['status'])
    op.create_index('ix_calendar_sync_logs_created_at', 'calendar_sync_logs', ['created_at'])
    op.create_index('ix_calendar_sync_logs_agency_created', 'calendar_sync_logs', ['agency_id', 'created_at'])

    # 5. calendar_webhook_subscriptions
    op.create_table(
        'calendar_webhook_subscriptions',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('connection_id', app.db.guid.GUID(), nullable=False),
        sa.Column('provider', calendar_provider_enum, nullable=False),
        sa.Column('external_subscription_id', sa.String(length=255), nullable=False),
        sa.Column('resource_id', sa.String(length=255), nullable=True),
        sa.Column('client_state_or_token', sa.String(length=255), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['connection_id'], ['calendar_connections.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_subscription_id', name='uq_calendar_webhook_subs_external_id'),
    )
    op.create_index('ix_calendar_webhook_subscriptions_agency_id', 'calendar_webhook_subscriptions', ['agency_id'])
    op.create_index('ix_calendar_webhook_subscriptions_connection_id', 'calendar_webhook_subscriptions', ['connection_id'])


def downgrade() -> None:
    op.drop_table('calendar_webhook_subscriptions')
    op.drop_table('calendar_sync_logs')
    op.drop_table('calendar_sync_jobs')
    op.drop_table('calendar_event_mappings')
    op.drop_table('calendar_connections')

    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        meeting_provider_enum.drop(bind, checkfirst=True)
        calendar_sync_operation_enum.drop(bind, checkfirst=True)
        calendar_sync_direction_enum.drop(bind, checkfirst=True)
        calendar_sync_status_enum.drop(bind, checkfirst=True)
        calendar_provider_enum.drop(bind, checkfirst=True)
