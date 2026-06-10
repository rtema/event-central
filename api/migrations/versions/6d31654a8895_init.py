"""init

Revision ID: 6d31654a8895
Revises: 
Create Date: 2026-06-10 17:35:21.129411
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '6d31654a8895'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id',
                  postgresql.UUID(
                      as_uuid=True),
                  nullable=False
                  ),
        sa.Column('email',
                  sa.String(length=320),
                  nullable=True
                  ),
        sa.Column('title',
                  sa.String(length=64),
                  nullable=True
                  ),
        sa.Column('salutation',
                  sa.String(length=64),
                  nullable=True
                  ),
        sa.Column('first_name',
                  sa.String(length=128),
                  nullable=False
                  ),
        sa.Column('last_name',
                  sa.String(length=128),
                  nullable=False
                  ),
        sa.Column('created_at',
                  sa.DateTime(timezone=True),
                  server_default=sa.text('now()'),
                  nullable=False
                  ),
        sa.Column('deleted_at',
                  sa.DateTime(timezone=True),
                  nullable=True
                  ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)

    op.create_table(
        'auth_challenges',
        sa.Column('id',
                  postgresql.UUID(as_uuid=True),
                  nullable=False
                  ),
        sa.Column('user_id',
                  postgresql.UUID(as_uuid=True),
                  nullable=True
                  ),
        sa.Column('purpose',
                  sa.String(length=32),
                  nullable=False
                  ),
        sa.Column('channel',
                  sa.String(length=16),
                  nullable=True
                  ),
        sa.Column('destination',
                  sa.String(length=320),
                  nullable=False
                  ),
        sa.Column('code_hash',
                  sa.String(length=512),
                  nullable=False
                  ),
        sa.Column('client_id',
                  sa.String(length=255),
                  nullable=True
                  ),
        sa.Column('scope',
                  sa.String(length=2048),
                  nullable=True
                  ),
        sa.Column('redirect_uri',
                  sa.String(length=2048),
                  nullable=True
                  ),
        sa.Column('expires_at',
                  sa.DateTime(timezone=True),
                  nullable=False
                  ),
        sa.Column('consumed_at',
                  sa.DateTime(timezone=True),
                  nullable=True
                  ),
        sa.Column('created_at',
                  sa.DateTime(timezone=True),
                  server_default=sa.text('now()'),
                  nullable=False
                  ),
        sa.ForeignKeyConstraint(['user_id'],
                                ['users.id'],
                                ondelete='CASCADE'
                                ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_auth_challenges_destination'),
        'auth_challenges', ['destination'], unique=False
    )
    op.create_index(
        op.f('ix_auth_challenges_user_id'),
        'auth_challenges', ['user_id'], unique=False
    )

    op.create_table(
        'refresh_tokens',
        sa.Column('id',
                  postgresql.UUID(
                      as_uuid=True),
                  nullable=False
                  ),
        sa.Column('user_id',
                  postgresql.UUID(as_uuid=True),
                  nullable=False
                  ),
        sa.Column('client_id',
                  sa.String(length=255),
                  nullable=True
                  ),
        sa.Column('scope',
                  sa.String(length=2048), nullable=False),
        sa.Column('expires_at', sa.DateTime(
            timezone=True), nullable=False),
        sa.Column('revoked_at', sa.DateTime(
            timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_refresh_tokens_user_id'),
        'refresh_tokens',
        ['user_id'],
        unique=False
    )

    op.create_table(
        'user_auth',
        sa.Column('id',
                  postgresql.UUID(as_uuid=True),
                  nullable=False
                  ),
        sa.Column('user_id',
                  postgresql.UUID(as_uuid=True),
                  nullable=False
                  ),
        sa.Column('method',
                  sa.String(length=32),
                  nullable=False
                  ),
        sa.Column('secret',
                  sa.String(length=512),
                  nullable=True
                  ),
        sa.Column('created_reason',
                  sa.String(length=32),
                  nullable=True
                  ),
        sa.Column('deleted_reason',
                  sa.String(length=32),
                  nullable=True
                  ),
        sa.Column('created_at',
                  sa.DateTime(timezone=True),
                  server_default=sa.text('now()'),
                  nullable=False
                  ),
        sa.Column('created_by',
                  sa.String(
                      length=128),
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
        sa.ForeignKeyConstraint(['user_id'],
                                ['users.id'],
                                ondelete='CASCADE'
                                ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_auth_user_id'),
                    'user_auth', ['user_id'], unique=False)

    op.create_table(
        'user_data_history',
        sa.Column('id',
                  postgresql.UUID(as_uuid=True),
                  nullable=False
                  ),
        sa.Column('user_id',
                  postgresql.UUID(as_uuid=True),
                  nullable=False
                  ),
        sa.Column('data',
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
        sa.ForeignKeyConstraint(['user_id'],
                                ['users.id'],
                                ondelete='CASCADE'
                                ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_data_history_user_id'),
                    'user_data_history', ['user_id'], unique=False)

    op.create_table(
        'user_history',
        sa.Column('id',
                  postgresql.UUID(
                      as_uuid=True),
                  nullable=False
                  ),
        sa.Column('user_id',
                  postgresql.UUID(as_uuid=True),
                  nullable=False
                  ),
        sa.Column('new_state',
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
        sa.ForeignKeyConstraint(['user_id'],
                                ['users.id'],
                                ondelete='CASCADE'
                                ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_history_user_id'),
                    'user_history', ['user_id'], unique=False)

    op.create_table(
        'user_scopes',
        sa.Column('id',
                  postgresql.UUID(as_uuid=True),
                  nullable=False
                  ),
        sa.Column('user_id', postgresql.UUID(as_uuid=True),
                  nullable=False
                  ),
        sa.Column('scope',
                  sa.String(length=128),
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
        sa.ForeignKeyConstraint(['user_id'],
                                ['users.id'],
                                ondelete='CASCADE'
                                ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_scopes_user_id'),
                    'user_scopes', ['user_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_scopes_user_id'), table_name='user_scopes')
    op.drop_table('user_scopes')
    op.drop_index(op.f('ix_user_history_user_id'), table_name='user_history')
    op.drop_table('user_history')
    op.drop_index(
        op.f('ix_user_data_history_user_id'), table_name='user_data_history')
    op.drop_table('user_data_history')
    op.drop_index(op.f('ix_user_auth_user_id'), table_name='user_auth')
    op.drop_table('user_auth')
    op.drop_index(
        op.f('ix_refresh_tokens_user_id'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
    op.drop_index(
        op.f('ix_auth_challenges_user_id'), table_name='auth_challenges')
    op.drop_index(
        op.f('ix_auth_challenges_destination'), table_name='auth_challenges')
    op.drop_table('auth_challenges')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
