"""fix email template versioning

Revision ID: cad0fe61f96e
Revises: 63212104ea02
Create Date: 2026-07-24 13:11:43.846950
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'cad0fe61f96e'
down_revision: str | None = '63212104ea02'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column('email_template_versions',
                  sa.Column('preview_text',
                            sa.Text(),
                            nullable=False
                            )
                  )
    op.drop_column('email_template_versions', 'previewText')


def downgrade() -> None:
    op.add_column('email_template_versions',
                  sa.Column('previewText', sa.TEXT(),
                            autoincrement=False,
                            nullable=False
                            )
                  )
    op.drop_column('email_template_versions', 'preview_text')
