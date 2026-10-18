"""Add Phase 4 matching engine models

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-10-15 03:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db.guid


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create job_match_runs table
    op.create_table(
        'job_match_runs',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('job_id', app.db.guid.GUID(), nullable=False),
        sa.Column('initiated_by', app.db.guid.GUID(), nullable=True),
        sa.Column('scoring_version', sa.String(length=50), nullable=False),
        sa.Column('matching_provider', sa.String(length=50), nullable=False),
        sa.Column('embedding_model', sa.String(length=100), nullable=True),
        sa.Column('candidate_count', sa.Integer(), nullable=False),
        sa.Column('completed_count', sa.Integer(), nullable=False),
        sa.Column('failed_count', sa.Integer(), nullable=False),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'PROCESSING', 'COMPLETED', 'PARTIALLY_COMPLETED', 'FAILED', name='jobmatchrunstatus'),
            nullable=False,
        ),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['initiated_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_job_match_runs_agency_id'), 'job_match_runs', ['agency_id'], unique=False)
    op.create_index(op.f('ix_job_match_runs_job_id'), 'job_match_runs', ['job_id'], unique=False)
    op.create_index(op.f('ix_job_match_runs_initiated_by'), 'job_match_runs', ['initiated_by'], unique=False)
    op.create_index(op.f('ix_job_match_runs_status'), 'job_match_runs', ['status'], unique=False)
    op.create_index('ix_match_runs_agency_job', 'job_match_runs', ['agency_id', 'job_id'], unique=False)
    op.create_index('ix_match_runs_agency_status', 'job_match_runs', ['agency_id', 'status'], unique=False)

    # 2. Create job_match_results table
    op.create_table(
        'job_match_results',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('job_id', app.db.guid.GUID(), nullable=False),
        sa.Column('candidate_id', app.db.guid.GUID(), nullable=False),
        sa.Column('match_run_id', app.db.guid.GUID(), nullable=False),
        sa.Column('overall_score', sa.Float(), nullable=False),
        sa.Column('required_skills_score', sa.Float(), nullable=False),
        sa.Column('experience_score', sa.Float(), nullable=False),
        sa.Column('preferred_skills_score', sa.Float(), nullable=False),
        sa.Column('project_relevance_score', sa.Float(), nullable=False),
        sa.Column('other_criteria_score', sa.Float(), nullable=False),
        sa.Column('matched_requirements_count', sa.Integer(), nullable=False),
        sa.Column('partial_requirements_count', sa.Integer(), nullable=False),
        sa.Column('missing_requirements_count', sa.Integer(), nullable=False),
        sa.Column('needs_verification_count', sa.Integer(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('strengths', sa.Text(), nullable=True),
        sa.Column('skill_gaps', sa.Text(), nullable=True),
        sa.Column('verification_items', sa.Text(), nullable=True),
        sa.Column('suggested_questions', sa.Text(), nullable=True),
        sa.Column('scoring_version', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['match_run_id'], ['job_match_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('match_run_id', 'candidate_id', name='uq_match_run_candidate'),
    )
    op.create_index(op.f('ix_job_match_results_agency_id'), 'job_match_results', ['agency_id'], unique=False)
    op.create_index(op.f('ix_job_match_results_job_id'), 'job_match_results', ['job_id'], unique=False)
    op.create_index(op.f('ix_job_match_results_candidate_id'), 'job_match_results', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_job_match_results_match_run_id'), 'job_match_results', ['match_run_id'], unique=False)
    op.create_index('ix_match_results_agency_job_score', 'job_match_results', ['agency_id', 'job_id', 'overall_score'], unique=False)
    op.create_index('ix_match_results_candidate', 'job_match_results', ['candidate_id'], unique=False)

    # 3. Create match_evidences table
    op.create_table(
        'match_evidences',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('match_result_id', app.db.guid.GUID(), nullable=False),
        sa.Column('job_requirement_id', app.db.guid.GUID(), nullable=True),
        sa.Column('criterion_name', sa.String(length=255), nullable=False),
        sa.Column('criterion_type', sa.String(length=50), nullable=False),
        sa.Column('expected_requirement', sa.Text(), nullable=False),
        sa.Column(
            'evidence_status',
            sa.Enum('DEMONSTRATED', 'PARTIAL', 'NOT_FOUND', 'NEEDS_VERIFICATION', name='matchstatus'),
            nullable=False,
        ),
        sa.Column('candidate_evidence', sa.Text(), nullable=True),
        sa.Column('source_resume_id', app.db.guid.GUID(), nullable=True),
        sa.Column('source_page', sa.Integer(), nullable=True),
        sa.Column('source_excerpt', sa.Text(), nullable=True),
        sa.Column('semantic_similarity', sa.Float(), nullable=True),
        sa.Column('score_contribution', sa.Float(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column(
            'verification_status',
            sa.Enum('UNREVIEWED', 'VERIFIED', 'CORRECTED', 'REJECTED', name='verificationstatus'),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_requirement_id'], ['job_requirements.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['match_result_id'], ['job_match_results.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['source_resume_id'], ['resumes.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_match_evidences_agency_id'), 'match_evidences', ['agency_id'], unique=False)
    op.create_index(op.f('ix_match_evidences_job_requirement_id'), 'match_evidences', ['job_requirement_id'], unique=False)
    op.create_index(op.f('ix_match_evidences_match_result_id'), 'match_evidences', ['match_result_id'], unique=False)
    op.create_index(op.f('ix_match_evidences_source_resume_id'), 'match_evidences', ['source_resume_id'], unique=False)
    op.create_index('ix_match_evidences_result', 'match_evidences', ['match_result_id'], unique=False)
    op.create_index('ix_match_evidences_status', 'match_evidences', ['agency_id', 'evidence_status'], unique=False)


def downgrade() -> None:
    op.drop_table('match_evidences')
    op.drop_table('job_match_results')
    op.drop_table('job_match_runs')
