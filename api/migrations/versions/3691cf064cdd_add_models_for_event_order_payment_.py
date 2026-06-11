"""add models for Event, Order, Payment, Invoice, InvoiceLineItem, Tax, DocumentTemplate, PublicDocumentTemplate

Revision ID: 3691cf064cdd
Revises: 6d31654a8895
Create Date: 2026-06-11 17:08:36.435535
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '3691cf064cdd'
down_revision: str | None = '6d31654a8895'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('document_templates',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('public_document_template_id', sa.String(length=128), nullable=True),
    sa.Column('html', sa.Text(), nullable=True),
    sa.Column('css', sa.Text(), nullable=True),
    sa.Column('fonts', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('images', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.String(length=128), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_document_templates_public_document_template_id'), 'document_templates', ['public_document_template_id'], unique=False)
    op.create_table('events',
    sa.Column('id', sa.String(length=128), nullable=False),
    sa.Column('label', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('start_dt', sa.DateTime(timezone=True), nullable=True),
    sa.Column('end_dt', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.String(length=128), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.String(length=128), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('orders',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('event_id', sa.String(length=128), nullable=False),
    sa.Column('external_id', sa.String(length=255), nullable=True),
    sa.Column('payment_link', sa.String(length=2048), nullable=True),
    sa.Column('link', sa.String(length=2048), nullable=True),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('recipient', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.String(length=128), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.String(length=128), nullable=True),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('event_id', 'external_id', name='uq_orders_event_external')
    )
    op.create_index(op.f('ix_orders_event_id'), 'orders', ['event_id'], unique=False)
    op.create_index(op.f('ix_orders_external_id'), 'orders', ['external_id'], unique=False)
    op.create_table('public_document_templates',
    sa.Column('id', sa.String(length=128), nullable=False),
    sa.Column('document_template_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('label', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_by', sa.String(length=128), nullable=True),
    sa.ForeignKeyConstraint(['document_template_id'], ['document_templates.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('invoices',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('event_id', sa.String(length=128), nullable=False),
    sa.Column('document_template_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('locale', sa.String(length=2), nullable=False),
    sa.Column('accounting_entity', sa.String(length=64), nullable=True),
    sa.Column('accounting_number', sa.Integer(), nullable=True),
    sa.Column('invoice_number', sa.String(length=128), nullable=True),
    sa.Column('invoice_type', sa.String(length=16), nullable=False),
    sa.Column('invoice_type_code', sa.String(length=8), nullable=False),
    sa.Column('issue_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('supplier', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('recipient', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('total_net', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('total_tax', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('total_gross', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('pdf_key', sa.String(length=512), nullable=True),
    sa.Column('xml_key', sa.String(length=512), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.String(length=128), nullable=False),
    sa.ForeignKeyConstraint(['document_template_id'], ['document_templates.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ondelete='RESTRICT'),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invoices_accounting_entity'), 'invoices', ['accounting_entity'], unique=False)
    op.create_index(op.f('ix_invoices_event_id'), 'invoices', ['event_id'], unique=False)
    op.create_index(op.f('ix_invoices_invoice_number'), 'invoices', ['invoice_number'], unique=False)
    op.create_index(op.f('ix_invoices_order_id'), 'invoices', ['order_id'], unique=False)
    op.create_table('payments',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('order_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('external_id', sa.String(length=255), nullable=True),
    sa.Column('provider', sa.String(length=128), nullable=True),
    sa.Column('method', sa.String(length=128), nullable=True),
    sa.Column('type', sa.String(length=16), nullable=False),
    sa.Column('status', sa.String(length=64), nullable=True),
    sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('currency', sa.String(length=3), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.String(length=128), nullable=False),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payments_external_id'), 'payments', ['external_id'], unique=False)
    op.create_index(op.f('ix_payments_order_id'), 'payments', ['order_id'], unique=False)
    op.create_table('taxes',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('external_id', sa.String(length=255), nullable=True),
    sa.Column('rate', sa.Numeric(precision=5, scale=2), nullable=False),
    sa.Column('label', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('type', sa.String(length=32), nullable=False),
    sa.Column('tax_exemption_reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('created_by', sa.String(length=128), nullable=False),
    sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_taxes_invoice_id'), 'taxes', ['invoice_id'], unique=False)
    op.create_table('invoice_line_items',
    sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False),
    sa.Column('tax_id', postgresql.UUID(as_uuid=True), nullable=True),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=14, scale=3), nullable=False),
    sa.Column('price_per_unit', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('name', sa.String(length=512), nullable=False),
    sa.Column('ticket', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('tax_category', sa.String(length=8), nullable=True),
    sa.Column('tax_rate', sa.Numeric(precision=5, scale=2), nullable=True),
    sa.Column('tax_scheme', sa.String(length=16), nullable=True),
    sa.Column('tax_exemption_reason', sa.Text(), nullable=True),
    sa.Column('tax_exemption_reason_code', sa.String(length=64), nullable=True),
    sa.Column('total_net', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('total_tax', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('total_gross', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['tax_id'], ['taxes.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_invoice_line_items_invoice_id'), 'invoice_line_items', ['invoice_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_invoice_line_items_invoice_id'), table_name='invoice_line_items')
    op.drop_table('invoice_line_items')
    op.drop_index(op.f('ix_taxes_invoice_id'), table_name='taxes')
    op.drop_table('taxes')
    op.drop_index(op.f('ix_payments_order_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_external_id'), table_name='payments')
    op.drop_table('payments')
    op.drop_index(op.f('ix_invoices_order_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_invoice_number'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_event_id'), table_name='invoices')
    op.drop_index(op.f('ix_invoices_accounting_entity'), table_name='invoices')
    op.drop_table('invoices')
    op.drop_table('public_document_templates')
    op.drop_index(op.f('ix_orders_external_id'), table_name='orders')
    op.drop_index(op.f('ix_orders_event_id'), table_name='orders')
    op.drop_table('orders')
    op.drop_table('events')
    op.drop_index(op.f('ix_document_templates_public_document_template_id'), table_name='document_templates')
    op.drop_table('document_templates')
