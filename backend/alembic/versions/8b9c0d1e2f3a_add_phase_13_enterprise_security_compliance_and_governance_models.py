"""Add Phase 13 enterprise security, compliance, and governance models
 
Revision ID: 8b9c0d1e2f3a
Revises: 7a8b9c0d1e2f
Create Date: 2026-10-17 23:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db.guid


# revision identifiers, used by Alembic.
revision: str = '8b9c0d1e2f3a'
down_revision: Union[str, Sequence[str], None] = '7a8b9c0d1e2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

audit_event_category_enum = sa.Enum(
    'AUTHENTICATION',
    'AUTHORIZATION',
    'DATA_ACCESS',
    'DATA_EXPORT',
    'ADMIN_ACTION',
    'SECURITY_EVENT',
    'PRIVACY_OP',
    name='auditeventcategory',
)

audit_severity_enum = sa.Enum(
    'LOW',
    'MEDIUM',
    'HIGH',
    'CRITICAL',
    name='auditseverity',
)

consent_type_enum = sa.Enum(
    'DATA_PROCESSING',
    'COMMUNICATION',
    'BACKGROUND_CHECK',
    'THIRD_PARTY_SHARING',
    name='consenttype',
)

privacy_request_type_enum = sa.Enum(
    'DATA_ACCESS',
    'DATA_CORRECTION',
    'DATA_DELETION',
    'RESTRICT_PROCESSING',
    'CONSENT_WITHDRAWAL',
    name='privacyrequesttype',
)

privacy_request_status_enum = sa.Enum(
    'PENDING',
    'IN_REVIEW',
    'COMPLETED',
    'REJECTED',
    'LEGAL_HOLD',
    name='privacyrequeststatus',
)

retention_category_enum = sa.Enum(
    'CANDIDATE_RECORDS',
    'RESUME_DOCUMENTS',
    'INTERVIEW_RECORDS',
    'NOTIFICATIONS',
    'AUDIT_LOGS',
    'AI_CONVERSATIONS',
    name='retentioncategory',
)

retention_action_enum = sa.Enum(
    'ANONYMIZE',
    'ARCHIVE',
    'DELETE',
    name='retentionaction',
)

retention_execution_type_enum = sa.Enum(
    'DRY_RUN',
    'EXECUTE',
    name='retentionexecutiontype',
)

retention_status_enum = sa.Enum(
    'COMPLETED',
    'FAILED',
    'CANCELLED',
    name='retentionstatus',
)


def upgrade() -> None:
    # 0. Add tokens_revoked_before column to users
    op.add_column('users', sa.Column('tokens_revoked_before', sa.DateTime(timezone=True), nullable=True))

    # 1. user_sessions
    op.create_table(
        'user_sessions',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('user_id', app.db.guid.GUID(), nullable=False),
        sa.Column('session_token_hash', sa.String(length=64), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('device_info', sa.String(length=100), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revocation_reason', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_user_sessions_agency_id'), 'user_sessions', ['agency_id'], unique=False)
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_sessions_is_active'), 'user_sessions', ['is_active'], unique=False)
    op.create_index(op.f('ix_user_sessions_session_token_hash'), 'user_sessions', ['session_token_hash'], unique=False)
    op.create_index('ix_user_sessions_user_active', 'user_sessions', ['user_id', 'is_active'], unique=False)
    op.create_index('ix_user_sessions_agency_active', 'user_sessions', ['agency_id', 'is_active'], unique=False)

    # 2. security_audit_events
    op.create_table(
        'security_audit_events',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('actor_user_id', app.db.guid.GUID(), nullable=True),
        sa.Column('actor_email', sa.String(length=255), nullable=True),
        sa.Column('event_category', audit_event_category_enum, nullable=False),
        sa.Column('severity', audit_severity_enum, nullable=False, server_default='LOW'),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('resource_type', sa.String(length=100), nullable=False),
        sa.Column('resource_id', sa.String(length=100), nullable=True),
        sa.Column('details_json', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(length=50), nullable=True),
        sa.Column('user_agent', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_security_audit_events_agency_id'), 'security_audit_events', ['agency_id'], unique=False)
    op.create_index(op.f('ix_security_audit_events_actor_user_id'), 'security_audit_events', ['actor_user_id'], unique=False)
    op.create_index(op.f('ix_security_audit_events_event_category'), 'security_audit_events', ['event_category'], unique=False)
    op.create_index(op.f('ix_security_audit_events_severity'), 'security_audit_events', ['severity'], unique=False)
    op.create_index(op.f('ix_security_audit_events_action'), 'security_audit_events', ['action'], unique=False)
    op.create_index(op.f('ix_security_audit_events_resource_type'), 'security_audit_events', ['resource_type'], unique=False)
    op.create_index('ix_sec_audit_agency_created', 'security_audit_events', ['agency_id', 'created_at'], unique=False)
    op.create_index('ix_sec_audit_agency_severity', 'security_audit_events', ['agency_id', 'severity'], unique=False)

    # 3. candidate_consent_records
    op.create_table(
        'candidate_consent_records',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('candidate_id', app.db.guid.GUID(), nullable=False),
        sa.Column('consent_type', consent_type_enum, nullable=False),
        sa.Column('is_granted', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('policy_version', sa.String(length=50), nullable=False, server_default='v1.0'),
        sa.Column('purpose', sa.String(length=255), nullable=False),
        sa.Column('channel', sa.String(length=50), nullable=False, server_default='APPLICATION_PORTAL'),
        sa.Column('granted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_candidate_consent_records_agency_id'), 'candidate_consent_records', ['agency_id'], unique=False)
    op.create_index(op.f('ix_candidate_consent_records_candidate_id'), 'candidate_consent_records', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_candidate_consent_records_consent_type'), 'candidate_consent_records', ['consent_type'], unique=False)
    op.create_index('ix_consent_agency_candidate', 'candidate_consent_records', ['agency_id', 'candidate_id'], unique=False)

    # 4. candidate_privacy_requests
    op.create_table(
        'candidate_privacy_requests',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('candidate_id', app.db.guid.GUID(), nullable=True),
        sa.Column('request_type', privacy_request_type_enum, nullable=False),
        sa.Column('status', privacy_request_status_enum, nullable=False, server_default='PENDING'),
        sa.Column('requested_by_email', sa.String(length=255), nullable=False),
        sa.Column('request_details', sa.Text(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('has_legal_hold', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('legal_hold_reason', sa.Text(), nullable=True),
        sa.Column('handled_by_user_id', app.db.guid.GUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['handled_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_candidate_privacy_requests_agency_id'), 'candidate_privacy_requests', ['agency_id'], unique=False)
    op.create_index(op.f('ix_candidate_privacy_requests_candidate_id'), 'candidate_privacy_requests', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_candidate_privacy_requests_request_type'), 'candidate_privacy_requests', ['request_type'], unique=False)
    op.create_index(op.f('ix_candidate_privacy_requests_status'), 'candidate_privacy_requests', ['status'], unique=False)
    op.create_index('ix_privacy_requests_agency_status', 'candidate_privacy_requests', ['agency_id', 'status'], unique=False)

    # 5. ai_governance_policies
    op.create_table(
        'ai_governance_policies',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('allowed_providers_json', sa.Text(), nullable=False, server_default='["OLLAMA", "HOSTED_OPEN_WEIGHT"]'),
        sa.Column('max_tokens_per_request', sa.Integer(), nullable=False, server_default='4000'),
        sa.Column('monthly_token_budget', sa.Integer(), nullable=False, server_default='500000'),
        sa.Column('require_pii_masking', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('safety_filter_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('updated_by_user_id', app.db.guid.GUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['updated_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agency_id', name='uq_ai_gov_policy_agency'),
    )
    op.create_index(op.f('ix_ai_governance_policies_agency_id'), 'ai_governance_policies', ['agency_id'], unique=True)

    # 6. ai_usage_logs
    op.create_table(
        'ai_usage_logs',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('user_id', app.db.guid.GUID(), nullable=True),
        sa.Column('feature_name', sa.String(length=100), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('completion_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_tokens', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('latency_ms', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('estimated_cost_usd', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('is_fallback', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('fallback_reason', sa.String(length=255), nullable=True),
        sa.Column('safety_filter_triggered', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_ai_usage_logs_agency_id'), 'ai_usage_logs', ['agency_id'], unique=False)
    op.create_index(op.f('ix_ai_usage_logs_user_id'), 'ai_usage_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_ai_usage_logs_feature_name'), 'ai_usage_logs', ['feature_name'], unique=False)
    op.create_index(op.f('ix_ai_usage_logs_provider'), 'ai_usage_logs', ['provider'], unique=False)
    op.create_index('ix_ai_usage_agency_created', 'ai_usage_logs', ['agency_id', 'created_at'], unique=False)
    op.create_index('ix_ai_usage_agency_feature', 'ai_usage_logs', ['agency_id', 'feature_name'], unique=False)

    # 7. data_retention_policies
    op.create_table(
        'data_retention_policies',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('data_category', retention_category_enum, nullable=False),
        sa.Column('retention_days', sa.Integer(), nullable=False, server_default='365'),
        sa.Column('action_type', retention_action_enum, nullable=False, server_default='ARCHIVE'),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('exempt_legal_holds', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('last_executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('agency_id', 'data_category', name='uq_agency_data_retention_category'),
    )
    op.create_index(op.f('ix_data_retention_policies_agency_id'), 'data_retention_policies', ['agency_id'], unique=False)
    op.create_index(op.f('ix_data_retention_policies_data_category'), 'data_retention_policies', ['data_category'], unique=False)

    # 8. retention_execution_logs
    op.create_table(
        'retention_execution_logs',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('policy_id', app.db.guid.GUID(), nullable=False),
        sa.Column('execution_type', retention_execution_type_enum, nullable=False),
        sa.Column('records_scanned', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_affected', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('records_exempted', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('status', retention_status_enum, nullable=False, server_default='COMPLETED'),
        sa.Column('executed_by_user_id', app.db.guid.GUID(), nullable=True),
        sa.Column('execution_summary_json', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['policy_id'], ['data_retention_policies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['executed_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_retention_execution_logs_agency_id'), 'retention_execution_logs', ['agency_id'], unique=False)
    op.create_index(op.f('ix_retention_execution_logs_policy_id'), 'retention_execution_logs', ['policy_id'], unique=False)


def downgrade() -> None:
    op.drop_table('retention_execution_logs')
    op.drop_table('data_retention_policies')
    op.drop_table('ai_usage_logs')
    op.drop_table('ai_governance_policies')
    op.drop_table('candidate_privacy_requests')
    op.drop_table('candidate_consent_records')
    op.drop_table('security_audit_events')
    op.drop_table('user_sessions')
    op.drop_column('users', 'tokens_revoked_before')
