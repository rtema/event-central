"""update invoicing tables

Revision ID: f30ff00addba
Revises: cfc2c412ac7a
Create Date: 2026-06-30 10:24:03.249767
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'f30ff00addba'
down_revision: str | None = 'cfc2c412ac7a'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index(op.f('ix_invoices_event_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_invoice_number'), table_name='invoices')
    op.create_index(op.f('ix_invoices_invoice_number'),
                    'invoices', ['invoice_number'], unique=True)
    op.drop_constraint(op.f('invoices_event_id_fkey'),
                       'invoices', type_='foreignkey')
    op.drop_column('invoices', 'event_id')
    op.add_column('orders', sa.Column('external_short_id',
                  sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_orders_external_short_id'),
                    'orders', ['external_short_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_orders_external_short_id'), table_name='orders')
    op.drop_column('orders', 'external_short_id')
    op.add_column('invoices', sa.Column('event_id', sa.VARCHAR(
        length=128), autoincrement=False, nullable=False))
    op.create_foreign_key(op.f('invoices_event_id_fkey'), 'invoices', 'events', [
                          'event_id'], ['id'], ondelete='RESTRICT')
    op.drop_index(op.f('ix_invoices_invoice_number'), table_name='invoices')
    op.create_index(op.f('ix_invoices_invoice_number'),
                    'invoices', ['invoice_number'], unique=False)
    op.create_index(op.f('ix_invoices_event_id'),
                    'invoices', ['event_id'], unique=False)
