"""Add Phase 12 predictive intelligence and workforce planning models
 
Revision ID: 7a8b9c0d1e2f
Revises: 6f7a8b9c0d1e
Create Date: 2026-10-17 22:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db.guid


# revision identifiers, used by Alembic.
revision: str = '7a8b9c0d1e2f'
down_revision: Union[str, Sequence[str], None] = '6f7a8b9c0d1e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

model_type_enum = sa.Enum(
    'TIME_TO_HIRE',
    'HIRING_DEMAND',
    'STAGE_DURATION',
    'CANDIDATE_DROP_OFF',
    name='modeltype',
)

prediction_algorithm_enum = sa.Enum(
    'RIDGE_REGRESSION',
    'RANDOM_FOREST',
    'EXPONENTIAL_SMOOTHING',
    'BASELINE_EMPIRICAL',
    name='predictionalgorithm',
)

forecast_type_enum = sa.Enum(
    'TIME_TO_HIRE',
    'DEMAND_30D',
    'DEMAND_60D',
    'DEMAND_90D',
    'APPLICATION_VOLUME',
    name='forecasttype',
)

confidence_level_enum = sa.Enum(
    'HIGH',
    'MEDIUM',
    'LOW',
    'PRELIMINARY',
    name='confidencelevel',
)

recruitment_risk_type_enum = sa.Enum(
    'PIPELINE_DEFICIT',
    'STAGE_STAGNATION',
    'DROP_OFF_VULNERABILITY',
    'SCHEDULING_BOTTLENECK',
    'EXPENSE_OVERRUN',
    name='recruitmentrisktype',
)

risk_severity_enum = sa.Enum(
    'CRITICAL',
    'HIGH',
    'MEDIUM',
    'LOW',
    name='riskseverity',
)

risk_status_enum = sa.Enum(
    'OPEN',
    'ACKNOWLEDGED',
    'MITIGATED',
    'DISMISSED',
    name='riskstatus',
)

recruiter_utilization_status_enum = sa.Enum(
    'OPTIMAL',
    'OVERLOADED',
    'UNDERUTILIZED',
    name='recruiterutilizationstatus',
)


def upgrade() -> None:
    # 1. prediction_model_versions
    op.create_table(
        'prediction_model_versions',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('model_type', model_type_enum, nullable=False),
        sa.Column('algorithm', prediction_algorithm_enum, nullable=False),
        sa.Column('version_tag', sa.String(length=100), nullable=False),
        sa.Column('training_sample_size', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('evaluation_metrics_json', sa.Text(), nullable=True),
        sa.Column('hyperparameters_json', sa.Text(), nullable=True),
        sa.Column('feature_names_json', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('trained_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_prediction_model_versions_agency_id'), 'prediction_model_versions', ['agency_id'], unique=False)
    op.create_index(op.f('ix_prediction_model_versions_model_type'), 'prediction_model_versions', ['model_type'], unique=False)
    op.create_index(op.f('ix_prediction_model_versions_is_active'), 'prediction_model_versions', ['is_active'], unique=False)
    op.create_index('ix_model_versions_agency_type_active', 'prediction_model_versions', ['agency_id', 'model_type', 'is_active'], unique=False)

    # 2. recruitment_forecasts
    op.create_table(
        'recruitment_forecasts',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('job_id', app.db.guid.GUID(), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('forecast_type', forecast_type_enum, nullable=False),
        sa.Column('predicted_value', sa.Float(), nullable=False),
        sa.Column('confidence_lower', sa.Float(), nullable=False),
        sa.Column('confidence_upper', sa.Float(), nullable=False),
        sa.Column('confidence_level', confidence_level_enum, nullable=False),
        sa.Column('is_baseline_fallback', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('factors_json', sa.Text(), nullable=True),
        sa.Column('model_version_id', app.db.guid.GUID(), nullable=True),
        sa.Column('horizon_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('forecast_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['model_version_id'], ['prediction_model_versions.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_recruitment_forecasts_agency_id'), 'recruitment_forecasts', ['agency_id'], unique=False)
    op.create_index(op.f('ix_recruitment_forecasts_job_id'), 'recruitment_forecasts', ['job_id'], unique=False)
    op.create_index(op.f('ix_recruitment_forecasts_department'), 'recruitment_forecasts', ['department'], unique=False)
    op.create_index(op.f('ix_recruitment_forecasts_forecast_type'), 'recruitment_forecasts', ['forecast_type'], unique=False)
    op.create_index('ix_forecasts_agency_type_date', 'recruitment_forecasts', ['agency_id', 'forecast_type', 'forecast_date'], unique=False)
    op.create_index('ix_forecasts_agency_job', 'recruitment_forecasts', ['agency_id', 'job_id'], unique=False)

    # 3. recruitment_risks
    op.create_table(
        'recruitment_risks',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('risk_type', recruitment_risk_type_enum, nullable=False),
        sa.Column('severity', risk_severity_enum, nullable=False),
        sa.Column('status', risk_status_enum, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('job_id', app.db.guid.GUID(), nullable=True),
        sa.Column('candidate_id', app.db.guid.GUID(), nullable=True),
        sa.Column('application_id', app.db.guid.GUID(), nullable=True),
        sa.Column('recruiter_id', app.db.guid.GUID(), nullable=True),
        sa.Column('evidence_payload_json', sa.Text(), nullable=True),
        sa.Column('recommended_action', sa.Text(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False, server_default='0.85'),
        sa.Column('acknowledged_by_user_id', app.db.guid.GUID(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['recruiter_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['acknowledged_by_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_recruitment_risks_agency_id'), 'recruitment_risks', ['agency_id'], unique=False)
    op.create_index(op.f('ix_recruitment_risks_risk_type'), 'recruitment_risks', ['risk_type'], unique=False)
    op.create_index(op.f('ix_recruitment_risks_severity'), 'recruitment_risks', ['severity'], unique=False)
    op.create_index(op.f('ix_recruitment_risks_status'), 'recruitment_risks', ['status'], unique=False)
    op.create_index(op.f('ix_recruitment_risks_job_id'), 'recruitment_risks', ['job_id'], unique=False)
    op.create_index(op.f('ix_recruitment_risks_candidate_id'), 'recruitment_risks', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_recruitment_risks_application_id'), 'recruitment_risks', ['application_id'], unique=False)
    op.create_index(op.f('ix_recruitment_risks_recruiter_id'), 'recruitment_risks', ['recruiter_id'], unique=False)
    op.create_index('ix_risks_agency_status_severity', 'recruitment_risks', ['agency_id', 'status', 'severity'], unique=False)
    op.create_index('ix_risks_agency_job', 'recruitment_risks', ['agency_id', 'job_id'], unique=False)

    # 4. capacity_snapshots
    op.create_table(
        'capacity_snapshots',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('recruiter_id', app.db.guid.GUID(), nullable=False),
        sa.Column('active_applications_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('upcoming_interviews_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('open_requisitions_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('workload_index', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('utilization_status', recruiter_utilization_status_enum, nullable=False),
        sa.Column('recommendations_json', sa.Text(), nullable=True),
        sa.Column('snapshot_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['recruiter_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_capacity_snapshots_agency_id'), 'capacity_snapshots', ['agency_id'], unique=False)
    op.create_index(op.f('ix_capacity_snapshots_recruiter_id'), 'capacity_snapshots', ['recruiter_id'], unique=False)
    op.create_index('ix_capacity_agency_recruiter_date', 'capacity_snapshots', ['agency_id', 'recruiter_id', 'snapshot_date'], unique=False)

    # 5. forecast_evaluations
    op.create_table(
        'forecast_evaluations',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('forecast_id', app.db.guid.GUID(), nullable=False),
        sa.Column('actual_value', sa.Float(), nullable=False),
        sa.Column('absolute_error', sa.Float(), nullable=False),
        sa.Column('percentage_error', sa.Float(), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['forecast_id'], ['recruitment_forecasts.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_forecast_evaluations_agency_id'), 'forecast_evaluations', ['agency_id'], unique=False)
    op.create_index(op.f('ix_forecast_evaluations_forecast_id'), 'forecast_evaluations', ['forecast_id'], unique=False)


def downgrade() -> None:
    op.drop_table('forecast_evaluations')
    op.drop_table('capacity_snapshots')
    op.drop_table('recruitment_risks')
    op.drop_table('recruitment_forecasts')
    op.drop_table('prediction_model_versions')
