"""init tables"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'f2cc307cab56'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(), unique=True, nullable=False),
        sa.Column('name', sa.String()),
    )
    op.create_table(
        'capabilities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), unique=True, nullable=False),
    )
    op.create_table(
        'user_capabilities',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('capability_id', sa.Integer(), sa.ForeignKey('capabilities.id'), nullable=False),
    )
    op.create_table(
        'user_ranges',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('range_low', sa.String()),
        sa.Column('range_high', sa.String()),
    )
    op.create_table(
        'materials',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('allowed_keys', sa.String()),
        sa.Column('required_capability_ids', sa.String()),
        sa.Column('scaffolding_capability_ids', sa.String()),
    )
    op.create_table(
        'focus_cards',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), unique=True, nullable=False),
    )
    op.create_table(
        'practice_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('started_at', sa.DateTime()),
        sa.Column('ended_at', sa.DateTime()),
    )
    op.create_table(
        'mini_sessions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('practice_session_id', sa.Integer(), sa.ForeignKey('practice_sessions.id'), nullable=False),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=False),
        sa.Column('key', sa.String()),
        sa.Column('focus_card_id', sa.Integer(), sa.ForeignKey('focus_cards.id')),
        sa.Column('goal_type', sa.String()),
    )
    op.create_table(
        'practice_attempts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('material_id', sa.Integer(), sa.ForeignKey('materials.id'), nullable=False),
        sa.Column('key', sa.String()),
        sa.Column('focus_card_id', sa.Integer(), sa.ForeignKey('focus_cards.id')),
        sa.Column('rating', sa.Integer()),
        sa.Column('fatigue', sa.Integer()),
        sa.Column('timestamp', sa.DateTime()),
    )

def downgrade():
    op.drop_table('practice_attempts')
    op.drop_table('mini_sessions')
    op.drop_table('practice_sessions')
    op.drop_table('focus_cards')
    op.drop_table('materials')
    op.drop_table('user_ranges')
    op.drop_table('user_capabilities')
    op.drop_table('capabilities')
    op.drop_table('users')