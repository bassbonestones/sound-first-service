"""Add tunes table for user-composed tunes with chord progressions.

Stores complete TuneComposerScore data for persistence across devices.
Includes chord_progressions_json for Phase 9.0 Chord Symbol Support.

Revision ID: 20260325_add_tunes
Revises: 20260311_keys_completed
Create Date: 2026-03-25

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '20260325_add_tunes'
down_revision = '20260311_keys_completed'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'tunes',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        
        # Score metadata
        sa.Column('clef', sa.String(), nullable=False, server_default='treble'),
        sa.Column('key_signature', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('time_signature_json', sa.String(), nullable=False, 
                  server_default='{"beats": 4, "beatUnit": 4}'),
        sa.Column('tempo', sa.Integer(), nullable=False, server_default='120'),
        
        # Score content (JSON strings)
        sa.Column('measures_json', sa.String(), nullable=False),
        sa.Column('chord_progressions_json', sa.String(), server_default='[]'),
        sa.Column('display_settings_json', sa.String(), 
                  server_default='{"showChordSymbols": true}'),
        sa.Column('playback_settings_json', sa.String(), server_default='{}'),
        
        # Import source (optional)
        sa.Column('imported_from', sa.String(), nullable=True),
        
        # Timestamps
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        
        # Soft delete
        sa.Column('is_archived', sa.Boolean(), server_default='false'),
    )
    
    # Index for user's tunes lookup
    op.create_index('ix_tunes_user_id', 'tunes', ['user_id'])


def downgrade():
    op.drop_index('ix_tunes_user_id', table_name='tunes')
    op.drop_table('tunes')
