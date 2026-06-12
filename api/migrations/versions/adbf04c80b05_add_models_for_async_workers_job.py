"""add models for async workers: Job

Revision ID: adbf04c80b05
Revises: 3691cf064cdd
Create Date: 2026-06-12 16:35:03.362605
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'adbf04c80b05'
down_revision: str | None = '3691cf064cdd'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'jobs',
        sa.Column('id',
                  postgresql.UUID(as_uuid=True),
                  nullable=False
                  ),
        sa.Column('type',
                  sa.String(length=128),
                  nullable=False
                  ),
        sa.Column('status',
                  sa.String(length=16),
                  nullable=False
                  ),
        sa.Column('payload',
                  postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False
                  ),
        sa.Column('result',
                  postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True
                  ),
        sa.Column('error',
                  sa.Text(),
                  nullable=True
                  ),
        sa.Column('attempts',
                  sa.Integer(),
                  nullable=False
                  ),
        sa.Column('max_attempts',
                  sa.Integer(),
                  nullable=False
                  ),
        sa.Column('available_at',
                  sa.DateTime(timezone=True),
                  nullable=False
                  ),
        sa.Column('locked_at',
                  sa.DateTime(timezone=True),
                  nullable=True
                  ),
        sa.Column('locked_by',
                  sa.String(length=128),
                  nullable=True
                  ),
        sa.Column('updated_at',
                  sa.DateTime(timezone=True),
                  nullable=False
                  ),
        sa.Column('created_at',
                  sa.DateTime(timezone=True),
                  server_default=sa.text('now()'),
                  nullable=False
                  ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_jobs_status'), 'jobs', ['status'], unique=False)
    op.create_index(op.f('ix_jobs_type'), 'jobs', ['type'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_jobs_type'), table_name='jobs')
    op.drop_index(op.f('ix_jobs_status'), table_name='jobs')
    op.drop_table('jobs')
