"""Add resume unique sha256 constraint and evidence corrected_value column

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-15 02:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update index on resumes to be UNIQUE per agency
    op.drop_index('ix_resumes_agency_sha256', table_name='resumes')
    op.create_index('ix_resumes_agency_sha256', 'resumes', ['agency_id', 'sha256_hash'], unique=True)

    # 2. Add corrected_value column to resume_evidences
    op.add_column('resume_evidences', sa.Column('corrected_value', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('resume_evidences', 'corrected_value')
    op.drop_index('ix_resumes_agency_sha256', table_name='resumes')
    op.create_index('ix_resumes_agency_sha256', 'resumes', ['agency_id', 'sha256_hash'], unique=False)
