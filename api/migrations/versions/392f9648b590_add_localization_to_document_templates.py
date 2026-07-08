"""add localization to document templates

Revision ID: 392f9648b590
Revises: 51d2b9b569d7
Create Date: 2026-07-08 18:58:41.023738
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '392f9648b590'
down_revision: str | None = '51d2b9b569d7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add as nullable so existing rows don't violate NOT NULL
    op.add_column('document_templates', sa.Column(
        'locale', sa.String(length=2), nullable=True))
    op.add_column('public_document_templates', sa.Column(
        'locale', sa.String(length=2), nullable=True))

    # Backfill every existing template with the default locale
    op.execute("UPDATE document_templates SET locale = 'de' WHERE locale IS NULL")
    op.execute("UPDATE public_document_templates SET locale = 'de' WHERE locale IS NULL")

    # enforce NOT NULL.
    op.alter_column('document_templates', 'locale', nullable=False)
    op.alter_column('public_document_templates', 'locale', nullable=False)


def downgrade() -> None:
    op.drop_column('public_document_templates', 'locale')
    op.drop_column('document_templates', 'locale')
