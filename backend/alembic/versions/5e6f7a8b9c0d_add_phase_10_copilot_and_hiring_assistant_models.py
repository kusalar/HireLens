"""Add Phase 10 copilot and hiring assistant models

Revision ID: 5e6f7a8b9c0d
Revises: 4d5e6f7a8b9c
Create Date: 2026-10-17 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db.guid


# revision identifiers, used by Alembic.
revision: str = '5e6f7a8b9c0d'
down_revision: Union[str, Sequence[str], None] = '4d5e6f7a8b9c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

copilot_action_type_enum = sa.Enum(
    'CHAT',
    'JOB_DESCRIPTION_GENERATE',
    'JOB_DESCRIPTION_IMPROVE',
    'JOB_DESCRIPTION_ANALYZE',
    'CANDIDATE_COMPARE',
    'INTERVIEW_PREPARE',
    'ANALYTICS_EXPLAIN',
    name='copilotactiontype',
)

copilot_message_role_enum = sa.Enum(
    'USER',
    'ASSISTANT',
    'SYSTEM',
    name='copilotmessagerole',
)

copilot_context_type_enum = sa.Enum(
    'AGENCY_OVERVIEW',
    'JOB',
    'CANDIDATE',
    'APPLICATION',
    'INTERVIEW',
    'ANALYTICS',
    name='copilotcontexttype',
)


def upgrade() -> None:
    # 1. copilot_conversations
    op.create_table(
        'copilot_conversations',
        sa.Column('id', app.db.guid.GUID(), primary_key=True, nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), sa.ForeignKey('agencies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', app.db.guid.GUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False, server_default='New Recruitment Conversation'),
        sa.Column('context_type', copilot_context_type_enum, nullable=False),
        sa.Column('context_id', app.db.guid.GUID(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_copilot_conversations_id', 'copilot_conversations', ['id'])
    op.create_index('ix_copilot_conversations_agency_id', 'copilot_conversations', ['agency_id'])
    op.create_index('ix_copilot_conversations_user_id', 'copilot_conversations', ['user_id'])
    op.create_index('ix_copilot_conversations_context_id', 'copilot_conversations', ['context_id'])
    op.create_index('ix_copilot_conv_agency_user', 'copilot_conversations', ['agency_id', 'user_id'])
    op.create_index('ix_copilot_conv_agency_updated', 'copilot_conversations', ['agency_id', 'updated_at'])

    # 2. copilot_messages
    op.create_table(
        'copilot_messages',
        sa.Column('id', app.db.guid.GUID(), primary_key=True, nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), sa.ForeignKey('agencies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('conversation_id', app.db.guid.GUID(), sa.ForeignKey('copilot_conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', copilot_message_role_enum, nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('context_snapshot', sa.Text(), nullable=True),
        sa.Column('sources', sa.Text(), nullable=True),
        sa.Column('model_used', sa.String(100), nullable=True),
        sa.Column('prompt_tokens', sa.Integer(), nullable=True),
        sa.Column('completion_tokens', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_copilot_messages_id', 'copilot_messages', ['id'])
    op.create_index('ix_copilot_messages_agency_id', 'copilot_messages', ['agency_id'])
    op.create_index('ix_copilot_messages_conversation_id', 'copilot_messages', ['conversation_id'])
    op.create_index('ix_copilot_messages_conv_created', 'copilot_messages', ['conversation_id', 'created_at'])

    # 3. copilot_audit_logs
    op.create_table(
        'copilot_audit_logs',
        sa.Column('id', app.db.guid.GUID(), primary_key=True, nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), sa.ForeignKey('agencies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', app.db.guid.GUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('conversation_id', app.db.guid.GUID(), sa.ForeignKey('copilot_conversations.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action_type', copilot_action_type_enum, nullable=False),
        sa.Column('target_entity_type', sa.String(50), nullable=True),
        sa.Column('target_entity_id', app.db.guid.GUID(), nullable=True),
        sa.Column('provider_used', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='SUCCESS'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_copilot_audit_logs_id', 'copilot_audit_logs', ['id'])
    op.create_index('ix_copilot_audit_logs_agency_id', 'copilot_audit_logs', ['agency_id'])
    op.create_index('ix_copilot_audit_logs_user_id', 'copilot_audit_logs', ['user_id'])
    op.create_index('ix_copilot_audit_logs_conversation_id', 'copilot_audit_logs', ['conversation_id'])
    op.create_index('ix_copilot_audit_logs_action_type', 'copilot_audit_logs', ['action_type'])
    op.create_index('ix_copilot_audit_logs_target_entity_id', 'copilot_audit_logs', ['target_entity_id'])
    op.create_index('ix_copilot_audit_agency_created', 'copilot_audit_logs', ['agency_id', 'created_at'])
    op.create_index('ix_copilot_audit_agency_action', 'copilot_audit_logs', ['agency_id', 'action_type'])


def downgrade() -> None:
    op.drop_table('copilot_audit_logs')
    op.drop_table('copilot_messages')
    op.drop_table('copilot_conversations')
