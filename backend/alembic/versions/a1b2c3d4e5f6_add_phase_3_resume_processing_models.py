"""Add Phase 3 resume processing models

Revision ID: a1b2c3d4e5f6
Revises: 7d6b2d68917a
Create Date: 2026-10-15 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db.guid


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '7d6b2d68917a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create resumes table
    op.create_table(
        'resumes',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('candidate_id', app.db.guid.GUID(), nullable=True),
        sa.Column('uploaded_by', app.db.guid.GUID(), nullable=True),
        sa.Column('original_filename', sa.String(length=255), nullable=False),
        sa.Column('stored_filename', sa.String(length=255), nullable=False),
        sa.Column('storage_key', sa.String(length=512), nullable=False),
        sa.Column('mime_type', sa.String(length=100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('sha256_hash', sa.String(length=64), nullable=False),
        sa.Column('page_count', sa.Integer(), nullable=True),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('language', sa.String(length=20), nullable=True),
        sa.Column(
            'processing_status',
            sa.Enum(
                'UPLOADED',
                'QUEUED',
                'EXTRACTING',
                'EXTRACTED',
                'PARSING',
                'REVIEW_REQUIRED',
                'COMPLETED',
                'FAILED',
                name='resumeprocessingstatus',
            ),
            nullable=False,
        ),
        sa.Column('upload_status', sa.String(length=50), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['candidate_id'], ['candidates.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_resumes_agency_id'), 'resumes', ['agency_id'], unique=False)
    op.create_index(op.f('ix_resumes_candidate_id'), 'resumes', ['candidate_id'], unique=False)
    op.create_index(op.f('ix_resumes_uploaded_by'), 'resumes', ['uploaded_by'], unique=False)
    op.create_index(op.f('ix_resumes_sha256_hash'), 'resumes', ['sha256_hash'], unique=False)
    op.create_index(op.f('ix_resumes_processing_status'), 'resumes', ['processing_status'], unique=False)
    op.create_index('ix_resumes_agency_sha256', 'resumes', ['agency_id', 'sha256_hash'], unique=False)
    op.create_index('ix_resumes_agency_status', 'resumes', ['agency_id', 'processing_status'], unique=False)

    # 2. Create resume_parse_runs table
    op.create_table(
        'resume_parse_runs',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('resume_id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model_name', sa.String(length=100), nullable=False),
        sa.Column('model_version', sa.String(length=50), nullable=True),
        sa.Column('extraction_method', sa.String(length=100), nullable=False),
        sa.Column(
            'status',
            sa.Enum('PENDING', 'RUNNING', 'COMPLETED', 'FAILED', name='parserunstatus'),
            nullable=False,
        ),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_duration_ms', sa.Integer(), nullable=True),
        sa.Column('error_code', sa.String(length=50), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_resume_parse_runs_agency_id'), 'resume_parse_runs', ['agency_id'], unique=False)
    op.create_index(op.f('ix_resume_parse_runs_resume_id'), 'resume_parse_runs', ['resume_id'], unique=False)
    op.create_index(op.f('ix_resume_parse_runs_status'), 'resume_parse_runs', ['status'], unique=False)

    # 3. Create resume_extracted_profiles table
    op.create_table(
        'resume_extracted_profiles',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('resume_id', app.db.guid.GUID(), nullable=False),
        sa.Column('parse_run_id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('extracted_name', sa.String(length=255), nullable=True),
        sa.Column('extracted_email', sa.String(length=255), nullable=True),
        sa.Column('extracted_phone', sa.String(length=100), nullable=True),
        sa.Column('extracted_location', sa.String(length=255), nullable=True),
        sa.Column('extracted_current_title', sa.String(length=255), nullable=True),
        sa.Column('extracted_summary', sa.Text(), nullable=True),
        sa.Column('extracted_experience_months', sa.Integer(), nullable=True),
        sa.Column('structured_extraction_json', sa.Text(), nullable=True),
        sa.Column('overall_confidence', sa.Float(), nullable=True),
        sa.Column(
            'recruiter_review_status',
            sa.Enum('PENDING', 'VERIFIED', 'CORRECTED', 'REJECTED', name='recruiterreviewstatus'),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parse_run_id'], ['resume_parse_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_resume_extracted_profiles_agency_id'), 'resume_extracted_profiles', ['agency_id'], unique=False)
    op.create_index(op.f('ix_resume_extracted_profiles_parse_run_id'), 'resume_extracted_profiles', ['parse_run_id'], unique=False)
    op.create_index(op.f('ix_resume_extracted_profiles_resume_id'), 'resume_extracted_profiles', ['resume_id'], unique=False)
    op.create_index(op.f('ix_resume_extracted_profiles_recruiter_review_status'), 'resume_extracted_profiles', ['recruiter_review_status'], unique=False)

    # 4. Create resume_evidences table
    op.create_table(
        'resume_evidences',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('parse_run_id', app.db.guid.GUID(), nullable=False),
        sa.Column('resume_id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('extracted_value', sa.Text(), nullable=False),
        sa.Column('source_page', sa.Integer(), nullable=True),
        sa.Column('source_excerpt', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column(
            'verification_status',
            sa.Enum('UNREVIEWED', 'VERIFIED', 'CORRECTED', 'REJECTED', name='verificationstatus'),
            nullable=False,
        ),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['parse_run_id'], ['resume_parse_runs.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['resume_id'], ['resumes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_resume_evidences_agency_id'), 'resume_evidences', ['agency_id'], unique=False)
    op.create_index(op.f('ix_resume_evidences_field_name'), 'resume_evidences', ['field_name'], unique=False)
    op.create_index(op.f('ix_resume_evidences_parse_run_id'), 'resume_evidences', ['parse_run_id'], unique=False)
    op.create_index(op.f('ix_resume_evidences_resume_id'), 'resume_evidences', ['resume_id'], unique=False)
    op.create_index(op.f('ix_resume_evidences_verification_status'), 'resume_evidences', ['verification_status'], unique=False)


def downgrade() -> None:
    op.drop_table('resume_evidences')
    op.drop_table('resume_extracted_profiles')
    op.drop_table('resume_parse_runs')
    op.drop_table('resumes')
