"""Add Phase 7 notification and communication models

Revision ID: 2b3c4d5e6f7a
Revises: 1a2b3c4d5e6f
Create Date: 2026-10-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db.guid


# revision identifiers, used by Alembic.
revision: str = '2b3c4d5e6f7a'
down_revision: Union[str, Sequence[str], None] = '1a2b3c4d5e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

notification_type_enum = sa.Enum(
    'INTERVIEW_SCHEDULED',
    'INTERVIEW_CONFIRMED',
    'INTERVIEW_RESCHEDULED',
    'INTERVIEW_CANCELLED',
    'INTERVIEW_COMPLETED',
    'APPLICATION_STATUS_UPDATED',
    'SYSTEM',
    name='notificationtype',
)

notification_delivery_status_enum = sa.Enum(
    'PENDING',
    'PROCESSING',
    'SENT',
    'FAILED',
    'DEAD_LETTER',
    name='notificationdeliverystatustype',
)


def upgrade() -> None:
    # 1. Create notifications table
    op.create_table(
        'notifications',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('recipient_user_id', app.db.guid.GUID(), nullable=False),
        sa.Column('notification_type', notification_type_enum, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('related_entity_type', sa.String(length=50), nullable=True),
        sa.Column('related_entity_id', app.db.guid.GUID(), nullable=True),
        sa.Column('is_read', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recipient_user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_notifications_agency_id', 'notifications', ['agency_id'])
    op.create_index('ix_notifications_recipient_user_id', 'notifications', ['recipient_user_id'])
    op.create_index('ix_notifications_is_read', 'notifications', ['is_read'])
    op.create_index(
        'ix_notifications_agency_recipient_read',
        'notifications',
        ['agency_id', 'recipient_user_id', 'is_read'],
    )
    op.create_index(
        'ix_notifications_agency_created',
        'notifications',
        ['agency_id', 'created_at'],
    )

    # 2. Create notification_preferences table
    op.create_table(
        'notification_preferences',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('email_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('interview_notifications_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('application_status_notifications_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('candidate_email_updates_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('default_timezone', sa.String(length=50), nullable=False, server_default='Asia/Kolkata'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agency_id', name='uq_notification_preferences_agency_id'),
    )
    op.create_index('ix_notification_preferences_agency_id', 'notification_preferences', ['agency_id'])

    # 3. Create email_delivery_logs table
    op.create_table(
        'email_delivery_logs',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('recipient_email', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False, server_default='console'),
        sa.Column('status', notification_delivery_status_enum, nullable=False),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key', name='uq_email_delivery_logs_idempotency_key'),
    )
    op.create_index('ix_email_delivery_logs_agency_id', 'email_delivery_logs', ['agency_id'])
    op.create_index('ix_email_delivery_logs_recipient_email', 'email_delivery_logs', ['recipient_email'])
    op.create_index('ix_email_delivery_logs_event_type', 'email_delivery_logs', ['event_type'])
    op.create_index('ix_email_delivery_logs_status', 'email_delivery_logs', ['status'])
    op.create_index('ix_delivery_logs_agency_status', 'email_delivery_logs', ['agency_id', 'status'])
    op.create_index('ix_delivery_logs_agency_created', 'email_delivery_logs', ['agency_id', 'created_at'])

    # 4. Create notification_outbox table
    op.create_table(
        'notification_outbox',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('idempotency_key', sa.String(length=255), nullable=False),
        sa.Column('recipient_email', sa.String(length=255), nullable=False),
        sa.Column('recipient_name', sa.String(length=255), nullable=True),
        sa.Column('subject', sa.String(length=255), nullable=False),
        sa.Column('body_html', sa.Text(), nullable=False),
        sa.Column('body_text', sa.Text(), nullable=False),
        sa.Column('status', notification_delivery_status_enum, nullable=False),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('max_retries', sa.Integer(), nullable=False, server_default='3'),
        sa.Column('next_retry_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key', name='uq_notification_outbox_idempotency_key'),
    )
    op.create_index('ix_notification_outbox_agency_id', 'notification_outbox', ['agency_id'])
    op.create_index('ix_notification_outbox_status', 'notification_outbox', ['status'])
    op.create_index('ix_notification_outbox_next_retry_at', 'notification_outbox', ['next_retry_at'])
    op.create_index('ix_outbox_status_next_retry', 'notification_outbox', ['status', 'next_retry_at'])
    op.create_index('ix_outbox_agency_status', 'notification_outbox', ['agency_id', 'status'])


def downgrade() -> None:
    op.drop_table('notification_outbox')
    op.drop_table('email_delivery_logs')
    op.drop_table('notification_preferences')
    op.drop_table('notifications')

    # Drop enums if on PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        notification_delivery_status_enum.drop(bind, checkfirst=True)
        notification_type_enum.drop(bind, checkfirst=True)
