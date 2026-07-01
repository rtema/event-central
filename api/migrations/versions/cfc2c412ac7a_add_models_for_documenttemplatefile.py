"""add models for DocumentTemplateFile

Revision ID: cfc2c412ac7a
Revises: bb5c2629011b
Create Date: 2026-06-17 18:35:45.154619
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = 'cfc2c412ac7a'
down_revision: str | None = 'bb5c2629011b'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'document_template_files',
        sa.Column('id',
                  postgresql.UUID(as_uuid=True),
                  nullable=False
                  ),
        sa.Column('document_template_id',
                  postgresql.UUID(as_uuid=True),
                  nullable=True
                  ),
        sa.Column('file_id',
                  postgresql.UUID(as_uuid=True),
                  nullable=True
                  ),
        sa.Column('type',
                  sa.String(length=256),
                  nullable=False
                  ),
        sa.Column('key',
                  sa.String(length=2048),
                  nullable=True
                  ),
        sa.Column('font_name',
                  sa.String(length=256),
                  nullable=True
                  ),
        sa.Column('font_weight',
                  sa.Integer(),
                  nullable=True
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
        sa.ForeignKeyConstraint(['document_template_id'], [
                                'document_templates.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(
            ['file_id'], ['files.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.drop_column('document_templates', 'fonts')
    op.drop_column('document_templates', 'images')


def downgrade() -> None:
    op.add_column('document_templates', sa.Column('images', postgresql.JSONB(
        astext_type=sa.Text()), autoincrement=False, nullable=False))
    op.add_column('document_templates', sa.Column('fonts', postgresql.JSONB(
        astext_type=sa.Text()), autoincrement=False, nullable=False))
    op.drop_table('document_template_files')
