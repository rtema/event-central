"""update tax handling

Revision ID: 51d2b9b569d7
Revises: f30ff00addba
Create Date: 2026-07-03 13:46:04.041048
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '51d2b9b569d7'
down_revision: str | None = 'f30ff00addba'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(op.f('ix_taxes_invoice_id'), table_name='taxes')
    op.drop_constraint(op.f('taxes_invoice_id_fkey'),
                       'taxes', type_='foreignkey')
    op.drop_column('taxes', 'invoice_id')


def downgrade() -> None:
    op.add_column('taxes', sa.Column('invoice_id', postgresql.UUID(
        as_uuid=True), autoincrement=False, nullable=False))
    op.create_foreign_key(op.f('taxes_invoice_id_fkey'), 'taxes', 'invoices', [
                          'invoice_id'], ['id'], ondelete='CASCADE')
    op.create_index(op.f('ix_taxes_invoice_id'), 'taxes',
                    ['invoice_id'], unique=False)
