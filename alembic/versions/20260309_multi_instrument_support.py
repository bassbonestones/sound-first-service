"""Add multi-instrument support

Add UserInstrument table for per-instrument state (Day0, range, resonant note).
Add is_global field to Capability to distinguish global vs instrument-specific capabilities.
Add instrument_id to UserCapability to track instrument-specific capability progress.

Revision ID: 20260309_multi_instrument
Revises: 4853451568ab
Create Date: 2026-03-09
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260309_multi_instrument'
down_revision = '4853451568ab'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add is_global to capabilities table (if not already exists from partial migration)
    try:
        op.add_column('capabilities',
            sa.Column('is_global', sa.Boolean(), nullable=True, server_default='1'))
    except Exception:
        pass  # Column already exists
    
    # Set all existing capabilities to global by default, then mark specific ones as instrument-specific
    op.execute("UPDATE capabilities SET is_global = 1 WHERE is_global IS NULL")
    
    # Mark first_note as instrument-specific (must be discovered per instrument)
    op.execute("UPDATE capabilities SET is_global = 0 WHERE name = 'first_note'")
    
    # 2. Create user_instruments table
    op.create_table('user_instruments',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('instrument_name', sa.String(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), default=False),
        sa.Column('clef', sa.String(), nullable=True),
        sa.Column('resonant_note', sa.String(), nullable=True),
        sa.Column('range_low', sa.String(), nullable=True),
        sa.Column('range_high', sa.String(), nullable=True),
        sa.Column('day0_completed', sa.Boolean(), default=False),
        sa.Column('day0_stage', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_practiced_at', sa.DateTime(), nullable=True),
    )
    
    op.create_index('ix_user_instrument_pair', 'user_instruments', ['user_id', 'instrument_name'], unique=True)
    op.create_index('ix_user_instrument_primary', 'user_instruments', ['user_id', 'is_primary'])
    
    # 3. Migrate existing user instrument data to user_instruments table
    # For users that have instrument set, create a UserInstrument record
    op.execute("""
        INSERT INTO user_instruments (user_id, instrument_name, is_primary, resonant_note, range_low, range_high, day0_completed, day0_stage, created_at)
        SELECT id, instrument, 1, resonant_note, range_low, range_high, day0_completed, day0_stage, datetime('now')
        FROM users
        WHERE instrument IS NOT NULL AND instrument != ''
    """)
    
    # 4. Add instrument_id to user_capabilities using batch mode for SQLite
    # SQLite doesn't support ALTER for foreign keys, so we just add the column without FK constraint
    op.add_column('user_capabilities',
        sa.Column('instrument_id', sa.Integer(), nullable=True))
    
    # Drop the old unique index and create the new one
    try:
        op.drop_index('ix_user_capability_pair', 'user_capabilities')
    except Exception:
        pass  # Index might not exist
    
    op.create_index('ix_user_capability_triple', 'user_capabilities', ['user_id', 'capability_id', 'instrument_id'], unique=True)
    op.create_index('ix_user_capability_instrument', 'user_capabilities', ['user_id', 'instrument_id'])


def downgrade() -> None:
    # Drop indexes on user_capabilities
    try:
        op.drop_index('ix_user_capability_triple', 'user_capabilities')
    except Exception:
        pass
    try:
        op.drop_index('ix_user_capability_instrument', 'user_capabilities')
    except Exception:
        pass
    
    # Recreate original index
    op.create_index('ix_user_capability_pair', 'user_capabilities', ['user_id', 'capability_id'], unique=True)
    
    # Drop instrument_id column
    op.drop_column('user_capabilities', 'instrument_id')
    
    # Drop user_instruments table
    op.drop_index('ix_user_instrument_pair', 'user_instruments')
    op.drop_index('ix_user_instrument_primary', 'user_instruments')
    op.drop_table('user_instruments')
    
    # Drop is_global from capabilities
    op.drop_column('capabilities', 'is_global')
