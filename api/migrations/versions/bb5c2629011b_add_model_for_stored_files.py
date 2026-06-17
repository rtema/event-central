"""add model for stored files

Revision ID: bb5c2629011b
Revises: adbf04c80b05
Create Date: 2026-06-17 16:59:23.296034
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'bb5c2629011b'
down_revision: str | None = 'adbf04c80b05'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'files',
        sa.Column('id',
                  postgresql.UUID(as_uuid=True),
                  nullable=False
                  ),
        sa.Column('label',
                  postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False
                  ),
        sa.Column('extension',
                  sa.String(length=16),
                  nullable=False
                  ),
        sa.Column('type',
                  sa.String(length=256),
                  nullable=False
                  ),
        sa.Column('mime',
                  sa.String(length=256),
                  nullable=False
                  ),
        sa.Column('published',
                  sa.Boolean(),
                  nullable=False
                  ),
        sa.Column('access_key',
                  sa.String(length=2048),
                  nullable=False
                  ),
        sa.Column('base_path',
                  sa.String(length=2048),
                  nullable=False
                  ),
        sa.Column('size',
                  sa.Integer(),
                  nullable=False
                  ),
        sa.Column('hash',
                  sa.String(length=64),
                  nullable=False
                  ),
        sa.Column('preview',
                  sa.Text(),
                  nullable=True
                  ),
        sa.Column('height',
                  sa.Integer(),
                  nullable=True
                  ),
        sa.Column('width',
                  sa.Integer(),
                  nullable=True
                  ),
        sa.Column('meta',
                  postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False
                  ),
        sa.Column('created_at',
                  sa.DateTime(timezone=True),
                  server_default=sa.text('now()'),
                  nullable=False
                  ),
        sa.Column('created_by',
                  sa.String(length=128),
                  nullable=False
                  ),
        sa.Column('deleted_at',
                  sa.DateTime(timezone=True),
                  nullable=True
                  ),
        sa.Column('deleted_by',
                  sa.String(length=128),
                  nullable=True
                  ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('access_key')
    )


def downgrade() -> None:
    op.drop_table('files')
