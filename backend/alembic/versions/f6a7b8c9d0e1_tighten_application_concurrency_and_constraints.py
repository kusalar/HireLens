"""Tighten application concurrency, OCC version, and database-level partial unique index

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-10-16 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add version column for optimistic concurrency control (OCC)
    with op.batch_alter_table('applications') as batch_op:
        batch_op.add_column(
            sa.Column('version', sa.Integer(), nullable=False, server_default='1')
        )

    # 2. Add database-level partial unique index to guarantee at most one active application
    # per (agency_id, job_id, candidate_id) where archived_at IS NULL and status != 'WITHDRAWN'.
    # Both SQLite (>= 3.8.0) and PostgreSQL natively support partial indexes with WHERE clauses.
    cond = sa.text("archived_at IS NULL AND status != 'WITHDRAWN'")
    op.create_index(
        'uq_active_application_per_job_candidate',
        'applications',
        ['agency_id', 'job_id', 'candidate_id'],
        unique=True,
        postgresql_where=cond,
        sqlite_where=cond,
    )


def downgrade() -> None:
    op.drop_index('uq_active_application_per_job_candidate', table_name='applications')
    with op.batch_alter_table('applications') as batch_op:
        batch_op.drop_column('version')
