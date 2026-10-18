"""Add Phase 11 workflow automation and orchestration models

Revision ID: 6f7a8b9c0d1e
Revises: 5e6f7a8b9c0d
Create Date: 2026-10-17 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db.guid


# revision identifiers, used by Alembic.
revision: str = '6f7a8b9c0d1e'
down_revision: Union[str, Sequence[str], None] = '5e6f7a8b9c0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

workflow_trigger_type_enum = sa.Enum(
    'CANDIDATE_CREATED',
    'RESUME_PROCESSED',
    'CANDIDATE_MATCHED',
    'APPLICATION_SUBMITTED',
    'APPLICATION_STAGE_CHANGED',
    'INTERVIEW_SCHEDULED',
    'INTERVIEW_RESCHEDULED',
    'INTERVIEW_COMPLETED',
    'FEEDBACK_SUBMITTED',
    'CANDIDATE_INACTIVE',
    name='workflowtriggertype',
)

workflow_action_type_enum = sa.Enum(
    'SEND_CANDIDATE_COMMUNICATION',
    'NOTIFY_RECRUITERS',
    'GENERATE_INTERVIEW_PREP',
    'CREATE_RECRUITER_TASK',
    'TRIGGER_CALENDAR_SYNC',
    'GENERATE_ANALYTICS_EVENT',
    'REQUEST_HUMAN_APPROVAL',
    name='workflowactiontype',
)

workflow_execution_status_enum = sa.Enum(
    'PENDING',
    'RUNNING',
    'WAITING_FOR_APPROVAL',
    'COMPLETED',
    'FAILED',
    'CANCELLED',
    'EXPIRED',
    name='workflowexecutionstatus',
)

workflow_step_status_enum = sa.Enum(
    'PENDING',
    'RUNNING',
    'COMPLETED',
    'FAILED',
    'SKIPPED',
    'WAITING_APPROVAL',
    name='workflowstepstatus',
)

workflow_approval_status_enum = sa.Enum(
    'PENDING',
    'APPROVED',
    'REJECTED',
    'EXPIRED',
    name='workflowapprovalstatus',
)

recruiter_task_status_enum = sa.Enum(
    'PENDING',
    'IN_PROGRESS',
    'COMPLETED',
    'CANCELLED',
    name='recruitertaskstatus',
)

recruiter_task_priority_enum = sa.Enum(
    'LOW',
    'MEDIUM',
    'HIGH',
    'URGENT',
    name='recruitertaskpriority',
)


def upgrade() -> None:
    # 1. recruitment_workflows
    op.create_table(
        'recruitment_workflows',
        sa.Column('id', app.db.guid.GUID(), primary_key=True, nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), sa.ForeignKey('agencies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('trigger_type', workflow_trigger_type_enum, nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_by_user_id', app.db.guid.GUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_recruitment_workflows_id', 'recruitment_workflows', ['id'])
    op.create_index('ix_recruitment_workflows_agency_id', 'recruitment_workflows', ['agency_id'])
    op.create_index('ix_recruitment_workflows_trigger_type', 'recruitment_workflows', ['trigger_type'])
    op.create_index('ix_recruitment_workflows_is_active', 'recruitment_workflows', ['is_active'])
    op.create_index('ix_workflows_agency_active', 'recruitment_workflows', ['agency_id', 'is_active'])
    op.create_index('ix_workflows_agency_trigger', 'recruitment_workflows', ['agency_id', 'trigger_type'])

    # 2. workflow_versions
    op.create_table(
        'workflow_versions',
        sa.Column('id', app.db.guid.GUID(), primary_key=True, nullable=False),
        sa.Column('workflow_id', app.db.guid.GUID(), sa.ForeignKey('recruitment_workflows.id', ondelete='CASCADE'), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('definition_json', sa.Text(), nullable=False),
        sa.Column('change_summary', sa.String(255), nullable=True),
        sa.Column('created_by_user_id', app.db.guid.GUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('workflow_id', 'version_number', name='uq_workflow_versions_workflow_version'),
    )
    op.create_index('ix_workflow_versions_id', 'workflow_versions', ['id'])
    op.create_index('ix_workflow_versions_workflow_id', 'workflow_versions', ['workflow_id'])

    # 3. workflow_executions
    op.create_table(
        'workflow_executions',
        sa.Column('id', app.db.guid.GUID(), primary_key=True, nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), sa.ForeignKey('agencies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workflow_id', app.db.guid.GUID(), sa.ForeignKey('recruitment_workflows.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workflow_version_id', app.db.guid.GUID(), sa.ForeignKey('workflow_versions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('trigger_event', workflow_trigger_type_enum, nullable=False),
        sa.Column('trigger_entity_type', sa.String(50), nullable=False),
        sa.Column('trigger_entity_id', app.db.guid.GUID(), nullable=True),
        sa.Column('status', workflow_execution_status_enum, nullable=False),
        sa.Column('idempotency_key', sa.String(255), nullable=False),
        sa.Column('context_snapshot', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), default=0, nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('agency_id', 'idempotency_key', name='uq_workflow_executions_agency_idempotency'),
    )
    op.create_index('ix_workflow_executions_id', 'workflow_executions', ['id'])
    op.create_index('ix_workflow_executions_agency_id', 'workflow_executions', ['agency_id'])
    op.create_index('ix_workflow_executions_workflow_id', 'workflow_executions', ['workflow_id'])
    op.create_index('ix_workflow_executions_status', 'workflow_executions', ['status'])
    op.create_index('ix_workflow_executions_idempotency_key', 'workflow_executions', ['idempotency_key'])
    op.create_index('ix_workflow_executions_trigger_entity_id', 'workflow_executions', ['trigger_entity_id'])
    op.create_index('ix_workflow_executions_agency_status', 'workflow_executions', ['agency_id', 'status'])
    op.create_index('ix_workflow_executions_agency_created', 'workflow_executions', ['agency_id', 'created_at'])

    # 4. workflow_execution_steps
    op.create_table(
        'workflow_execution_steps',
        sa.Column('id', app.db.guid.GUID(), primary_key=True, nullable=False),
        sa.Column('execution_id', app.db.guid.GUID(), sa.ForeignKey('workflow_executions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_index', sa.Integer(), nullable=False),
        sa.Column('action_type', workflow_action_type_enum, nullable=False),
        sa.Column('action_config', sa.Text(), nullable=False),
        sa.Column('status', workflow_step_status_enum, nullable=False),
        sa.Column('input_payload', sa.Text(), nullable=True),
        sa.Column('output_payload', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_workflow_execution_steps_id', 'workflow_execution_steps', ['id'])
    op.create_index('ix_workflow_execution_steps_execution_id', 'workflow_execution_steps', ['execution_id'])
    op.create_index('ix_workflow_steps_exec_index', 'workflow_execution_steps', ['execution_id', 'step_index'])

    # 5. workflow_approvals
    op.create_table(
        'workflow_approvals',
        sa.Column('id', app.db.guid.GUID(), primary_key=True, nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), sa.ForeignKey('agencies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('execution_id', app.db.guid.GUID(), sa.ForeignKey('workflow_executions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('step_id', app.db.guid.GUID(), sa.ForeignKey('workflow_execution_steps.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', workflow_approval_status_enum, nullable=False),
        sa.Column('requested_action', workflow_action_type_enum, nullable=False),
        sa.Column('action_payload', sa.Text(), nullable=True),
        sa.Column('assigned_role', sa.String(50), nullable=False, server_default='AGENCY_ADMIN'),
        sa.Column('assigned_user_id', app.db.guid.GUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('approved_by_user_id', app.db.guid.GUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_workflow_approvals_id', 'workflow_approvals', ['id'])
    op.create_index('ix_workflow_approvals_agency_id', 'workflow_approvals', ['agency_id'])
    op.create_index('ix_workflow_approvals_execution_id', 'workflow_approvals', ['execution_id'])
    op.create_index('ix_workflow_approvals_step_id', 'workflow_approvals', ['step_id'])
    op.create_index('ix_workflow_approvals_status', 'workflow_approvals', ['status'])
    op.create_index('ix_workflow_approvals_expires_at', 'workflow_approvals', ['expires_at'])
    op.create_index('ix_workflow_approvals_agency_status', 'workflow_approvals', ['agency_id', 'status'])
    op.create_index('ix_workflow_approvals_expires', 'workflow_approvals', ['status', 'expires_at'])

    # 6. recruiter_tasks
    op.create_table(
        'recruiter_tasks',
        sa.Column('id', app.db.guid.GUID(), primary_key=True, nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), sa.ForeignKey('agencies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('priority', recruiter_task_priority_enum, nullable=False),
        sa.Column('status', recruiter_task_status_enum, nullable=False),
        sa.Column('assigned_to_user_id', app.db.guid.GUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_by_user_id', app.db.guid.GUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('candidate_id', app.db.guid.GUID(), sa.ForeignKey('candidates.id', ondelete='SET NULL'), nullable=True),
        sa.Column('job_id', app.db.guid.GUID(), sa.ForeignKey('jobs.id', ondelete='SET NULL'), nullable=True),
        sa.Column('application_id', app.db.guid.GUID(), sa.ForeignKey('applications.id', ondelete='SET NULL'), nullable=True),
        sa.Column('interview_id', app.db.guid.GUID(), sa.ForeignKey('interviews.id', ondelete='SET NULL'), nullable=True),
        sa.Column('execution_id', app.db.guid.GUID(), sa.ForeignKey('workflow_executions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_recruiter_tasks_id', 'recruiter_tasks', ['id'])
    op.create_index('ix_recruiter_tasks_agency_id', 'recruiter_tasks', ['agency_id'])
    op.create_index('ix_recruiter_tasks_status', 'recruiter_tasks', ['status'])
    op.create_index('ix_recruiter_tasks_assigned_to_user_id', 'recruiter_tasks', ['assigned_to_user_id'])
    op.create_index('ix_recruiter_tasks_candidate_id', 'recruiter_tasks', ['candidate_id'])
    op.create_index('ix_recruiter_tasks_job_id', 'recruiter_tasks', ['job_id'])
    op.create_index('ix_recruiter_tasks_application_id', 'recruiter_tasks', ['application_id'])
    op.create_index('ix_recruiter_tasks_interview_id', 'recruiter_tasks', ['interview_id'])
    op.create_index('ix_recruiter_tasks_due_date', 'recruiter_tasks', ['due_date'])
    op.create_index('ix_recruiter_tasks_agency_status', 'recruiter_tasks', ['agency_id', 'status'])
    op.create_index('ix_recruiter_tasks_assigned_status', 'recruiter_tasks', ['assigned_to_user_id', 'status'])

    # 7. workflow_audit_logs
    op.create_table(
        'workflow_audit_logs',
        sa.Column('id', app.db.guid.GUID(), primary_key=True, nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), sa.ForeignKey('agencies.id', ondelete='CASCADE'), nullable=False),
        sa.Column('workflow_id', app.db.guid.GUID(), sa.ForeignKey('recruitment_workflows.id', ondelete='SET NULL'), nullable=True),
        sa.Column('execution_id', app.db.guid.GUID(), sa.ForeignKey('workflow_executions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_id', app.db.guid.GUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_workflow_audit_logs_id', 'workflow_audit_logs', ['id'])
    op.create_index('ix_workflow_audit_logs_agency_id', 'workflow_audit_logs', ['agency_id'])
    op.create_index('ix_workflow_audit_logs_workflow_id', 'workflow_audit_logs', ['workflow_id'])
    op.create_index('ix_workflow_audit_logs_execution_id', 'workflow_audit_logs', ['execution_id'])
    op.create_index('ix_workflow_audit_logs_created_at', 'workflow_audit_logs', ['created_at'])
    op.create_index('ix_workflow_audit_agency_created', 'workflow_audit_logs', ['agency_id', 'created_at'])


def downgrade() -> None:
    op.drop_table('workflow_audit_logs')
    op.drop_table('recruiter_tasks')
    op.drop_table('workflow_approvals')
    op.drop_table('workflow_execution_steps')
    op.drop_table('workflow_executions')
    op.drop_table('workflow_versions')
    op.drop_table('recruitment_workflows')
