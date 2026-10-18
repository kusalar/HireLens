"""Add Phase 8 recruitment expenses and candidate source models

Revision ID: 3c4d5e6f7a8b
Revises: 2b3c4d5e6f7a
Create Date: 2026-10-17 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import app.db.guid


# revision identifiers, used by Alembic.
revision: str = '3c4d5e6f7a8b'
down_revision: Union[str, Sequence[str], None] = '2b3c4d5e6f7a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

expense_category_enum = sa.Enum(
    'JOB_ADVERTISING',
    'RECRUITMENT_PLATFORMS',
    'AGENCY_FEES',
    'ASSESSMENT_COSTS',
    'INTERVIEW_EXPENSES',
    'OTHER',
    name='expensecategory',
)


def upgrade() -> None:
    # 1. Add source column to candidates
    op.add_column('candidates', sa.Column('source', sa.String(length=100), nullable=True))
    op.create_index('ix_candidates_agency_source', 'candidates', ['agency_id', 'source'])

    # 2. Add supporting indexes to applications
    op.create_index('ix_applications_agency_source', 'applications', ['agency_id', 'source'])
    op.create_index('ix_applications_agency_applied_at', 'applications', ['agency_id', 'applied_at'])

    # 3. Create recruitment_expenses table
    op.create_table(
        'recruitment_expenses',
        sa.Column('id', app.db.guid.GUID(), nullable=False),
        sa.Column('agency_id', app.db.guid.GUID(), nullable=False),
        sa.Column('job_id', app.db.guid.GUID(), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False, server_default='INR'),
        sa.Column('category', expense_category_enum, nullable=False),
        sa.Column('expense_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_by', app.db.guid.GUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['agency_id'], ['agencies.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['job_id'], ['jobs.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_recruitment_expenses_agency_id', 'recruitment_expenses', ['agency_id'])
    op.create_index('ix_recruitment_expenses_job_id', 'recruitment_expenses', ['job_id'])
    op.create_index('ix_recruitment_expenses_category', 'recruitment_expenses', ['category'])
    op.create_index('ix_recruitment_expenses_expense_date', 'recruitment_expenses', ['expense_date'])
    op.create_index(
        'ix_recruitment_expenses_agency_date',
        'recruitment_expenses',
        ['agency_id', 'expense_date'],
    )
    op.create_index(
        'ix_recruitment_expenses_agency_job',
        'recruitment_expenses',
        ['agency_id', 'job_id'],
    )
    op.create_index(
        'ix_recruitment_expenses_agency_category',
        'recruitment_expenses',
        ['agency_id', 'category'],
    )


def downgrade() -> None:
    # 1. Drop recruitment_expenses table and indexes
    op.drop_index('ix_recruitment_expenses_agency_category', table_name='recruitment_expenses')
    op.drop_index('ix_recruitment_expenses_agency_job', table_name='recruitment_expenses')
    op.drop_index('ix_recruitment_expenses_agency_date', table_name='recruitment_expenses')
    op.drop_index('ix_recruitment_expenses_expense_date', table_name='recruitment_expenses')
    op.drop_index('ix_recruitment_expenses_category', table_name='recruitment_expenses')
    op.drop_index('ix_recruitment_expenses_job_id', table_name='recruitment_expenses')
    op.drop_index('ix_recruitment_expenses_agency_id', table_name='recruitment_expenses')
    op.drop_table('recruitment_expenses')
    expense_category_enum.drop(op.get_bind(), checkfirst=True)

    # 2. Drop applications indexes
    op.drop_index('ix_applications_agency_applied_at', table_name='applications')
    op.drop_index('ix_applications_agency_source', table_name='applications')

    # 3. Drop candidates source column and index
    op.drop_index('ix_candidates_agency_source', table_name='candidates')
    op.drop_column('candidates', 'source')
