"""Add event broadcasting tables

Revision ID: add_event_broadcasting_tables
Revises: add_forwarder_priority_grouping_templates
Create Date: 2024-01-01 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_event_broadcasting_tables'
down_revision = 'add_forwarder_priority_grouping_templates'
branch_labels = None
depends_on = None


def upgrade():
    # Create events table (SQLite compatible)
    op.create_table('events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=False),  # Use String for UUID in SQLite
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('event_category', sa.String(length=50), nullable=False),
        sa.Column('event_source', sa.String(length=100), nullable=False),
        sa.Column('event_data', sa.Text(), nullable=False),  # Use Text instead of JSON for SQLite
        sa.Column('user_id', sa.String(length=100), nullable=True),
        sa.Column('session_id', sa.String(length=100), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('tags', sa.Text(), nullable=True),  # Use Text instead of JSON for SQLite
        sa.Column('metadata', sa.Text(), nullable=True),  # Use Text instead of JSON for SQLite
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('processed_at', sa.DateTime(), nullable=True),
        sa.Column('is_processed', sa.Boolean(), nullable=False),
        sa.Column('retry_count', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for events table
    op.create_index('idx_events_type_created', 'events', ['event_type', 'created_at'])
    op.create_index('idx_events_category_created', 'events', ['event_category', 'created_at'])
    op.create_index('idx_events_user_created', 'events', ['user_id', 'created_at'])
    op.create_index('idx_events_severity_created', 'events', ['severity', 'created_at'])
    op.create_index('idx_events_processed', 'events', ['is_processed', 'created_at'])
    op.create_index(op.f('ix_events_event_id'), 'events', ['event_id'], unique=True)
    op.create_index(op.f('ix_events_event_type'), 'events', ['event_type'])
    op.create_index(op.f('ix_events_event_category'), 'events', ['event_category'])
    op.create_index(op.f('ix_events_user_id'), 'events', ['user_id'])
    op.create_index(op.f('ix_events_session_id'), 'events', ['session_id'])
    op.create_index(op.f('ix_events_is_processed'), 'events', ['is_processed'])
    op.create_index(op.f('ix_events_created_at'), 'events', ['created_at'])
    
    # Create event_subscriptions table (SQLite compatible)
    op.create_table('event_subscriptions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.String(length=36), nullable=False),  # Use String for UUID in SQLite
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('connection_id', sa.String(length=100), nullable=True),
        sa.Column('event_type', sa.String(length=100), nullable=True),
        sa.Column('event_category', sa.String(length=50), nullable=True),
        sa.Column('event_source', sa.String(length=100), nullable=True),
        sa.Column('severity_filter', sa.Text(), nullable=True),  # Use Text instead of JSON for SQLite
        sa.Column('tag_filters', sa.Text(), nullable=True),  # Use Text instead of JSON for SQLite
        sa.Column('user_filters', sa.Text(), nullable=True),  # Use Text instead of JSON for SQLite
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('event_id', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for event_subscriptions table
    op.create_index('idx_subscriptions_user_active', 'event_subscriptions', ['user_id', 'is_active'])
    op.create_index('idx_subscriptions_connection_active', 'event_subscriptions', ['connection_id', 'is_active'])
    op.create_index('idx_subscriptions_type_active', 'event_subscriptions', ['event_type', 'is_active'])
    op.create_index('idx_subscriptions_expires', 'event_subscriptions', ['expires_at'])
    op.create_index(op.f('ix_event_subscriptions_subscription_id'), 'event_subscriptions', ['subscription_id'], unique=True)
    op.create_index(op.f('ix_event_subscriptions_user_id'), 'event_subscriptions', ['user_id'])
    op.create_index(op.f('ix_event_subscriptions_connection_id'), 'event_subscriptions', ['connection_id'])
    op.create_index(op.f('ix_event_subscriptions_event_type'), 'event_subscriptions', ['event_type'])
    op.create_index(op.f('ix_event_subscriptions_event_category'), 'event_subscriptions', ['event_category'])
    op.create_index(op.f('ix_event_subscriptions_event_source'), 'event_subscriptions', ['event_source'])
    op.create_index(op.f('ix_event_subscriptions_is_active'), 'event_subscriptions', ['is_active'])
    op.create_index(op.f('ix_event_subscriptions_expires_at'), 'event_subscriptions', ['expires_at'])
    
    # Create event_deliveries table (SQLite compatible)
    op.create_table('event_deliveries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('delivery_id', sa.String(length=36), nullable=False),  # Use String for UUID in SQLite
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('subscription_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('connection_id', sa.String(length=100), nullable=True),
        sa.Column('delivery_method', sa.String(length=50), nullable=False),
        sa.Column('delivery_status', sa.String(length=20), nullable=False),
        sa.Column('delivery_attempts', sa.Integer(), nullable=False),
        sa.Column('max_attempts', sa.Integer(), nullable=False),
        sa.Column('last_attempt_at', sa.DateTime(), nullable=True),
        sa.Column('delivered_at', sa.DateTime(), nullable=True),
        sa.Column('failed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_after', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.ForeignKeyConstraint(['subscription_id'], ['event_subscriptions.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for event_deliveries table
    op.create_index('idx_deliveries_status_created', 'event_deliveries', ['delivery_status', 'created_at'])
    op.create_index('idx_deliveries_user_status', 'event_deliveries', ['user_id', 'delivery_status'])
    op.create_index('idx_deliveries_retry', 'event_deliveries', ['retry_after', 'delivery_status'])
    op.create_index('idx_deliveries_event_user', 'event_deliveries', ['event_id', 'user_id'])
    op.create_index(op.f('ix_event_deliveries_delivery_id'), 'event_deliveries', ['delivery_id'], unique=True)
    op.create_index(op.f('ix_event_deliveries_event_id'), 'event_deliveries', ['event_id'])
    op.create_index(op.f('ix_event_deliveries_subscription_id'), 'event_deliveries', ['subscription_id'])
    op.create_index(op.f('ix_event_deliveries_user_id'), 'event_deliveries', ['user_id'])
    op.create_index(op.f('ix_event_deliveries_connection_id'), 'event_deliveries', ['connection_id'])
    op.create_index(op.f('ix_event_deliveries_delivery_status'), 'event_deliveries', ['delivery_status'])
    op.create_index(op.f('ix_event_deliveries_retry_after'), 'event_deliveries', ['retry_after'])
    op.create_index(op.f('ix_event_deliveries_created_at'), 'event_deliveries', ['created_at'])
    
    # Create event_filters table (SQLite compatible)
    op.create_table('event_filters',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filter_id', sa.String(length=36), nullable=False),  # Use String for UUID in SQLite
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('filter_config', sa.Text(), nullable=False),  # Use Text instead of JSON for SQLite
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.String(length=100), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for event_filters table
    op.create_index(op.f('ix_event_filters_filter_id'), 'event_filters', ['filter_id'], unique=True)
    op.create_index(op.f('ix_event_filters_is_active'), 'event_filters', ['is_active'])
    
    # Create event_replays table (SQLite compatible)
    op.create_table('event_replays',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('replay_id', sa.String(length=36), nullable=False),  # Use String for UUID in SQLite
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('user_id', sa.String(length=100), nullable=False),
        sa.Column('filter_config', sa.Text(), nullable=False),  # Use Text instead of JSON for SQLite
        sa.Column('replay_speed', sa.Integer(), nullable=False),
        sa.Column('start_time', sa.DateTime(), nullable=False),
        sa.Column('end_time', sa.DateTime(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('progress', sa.Integer(), nullable=False),
        sa.Column('total_events', sa.Integer(), nullable=False),
        sa.Column('processed_events', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for event_replays table
    op.create_index('idx_replays_user_status', 'event_replays', ['user_id', 'status'])
    op.create_index('idx_replays_status_created', 'event_replays', ['status', 'created_at'])
    op.create_index(op.f('ix_event_replays_replay_id'), 'event_replays', ['replay_id'], unique=True)
    op.create_index(op.f('ix_event_replays_user_id'), 'event_replays', ['user_id'])
    op.create_index(op.f('ix_event_replays_status'), 'event_replays', ['status'])


def downgrade():
    # Drop event_replays table
    op.drop_index(op.f('ix_event_replays_status'), table_name='event_replays')
    op.drop_index(op.f('ix_event_replays_user_id'), table_name='event_replays')
    op.drop_index(op.f('ix_event_replays_replay_id'), table_name='event_replays')
    op.drop_index('idx_replays_status_created', table_name='event_replays')
    op.drop_index('idx_replays_user_status', table_name='event_replays')
    op.drop_table('event_replays')
    
    # Drop event_filters table
    op.drop_index(op.f('ix_event_filters_is_active'), table_name='event_filters')
    op.drop_index(op.f('ix_event_filters_filter_id'), table_name='event_filters')
    op.drop_table('event_filters')
    
    # Drop event_deliveries table
    op.drop_index(op.f('ix_event_deliveries_created_at'), table_name='event_deliveries')
    op.drop_index(op.f('ix_event_deliveries_retry_after'), table_name='event_deliveries')
    op.drop_index(op.f('ix_event_deliveries_delivery_status'), table_name='event_deliveries')
    op.drop_index(op.f('ix_event_deliveries_connection_id'), table_name='event_deliveries')
    op.drop_index(op.f('ix_event_deliveries_user_id'), table_name='event_deliveries')
    op.drop_index(op.f('ix_event_deliveries_subscription_id'), table_name='event_deliveries')
    op.drop_index(op.f('ix_event_deliveries_event_id'), table_name='event_deliveries')
    op.drop_index(op.f('ix_event_deliveries_delivery_id'), table_name='event_deliveries')
    op.drop_index('idx_deliveries_event_user', table_name='event_deliveries')
    op.drop_index('idx_deliveries_retry', table_name='event_deliveries')
    op.drop_index('idx_deliveries_user_status', table_name='event_deliveries')
    op.drop_index('idx_deliveries_status_created', table_name='event_deliveries')
    op.drop_table('event_deliveries')
    
    # Drop event_subscriptions table
    op.drop_index(op.f('ix_event_subscriptions_expires_at'), table_name='event_subscriptions')
    op.drop_index(op.f('ix_event_subscriptions_is_active'), table_name='event_subscriptions')
    op.drop_index(op.f('ix_event_subscriptions_event_source'), table_name='event_subscriptions')
    op.drop_index(op.f('ix_event_subscriptions_event_category'), table_name='event_subscriptions')
    op.drop_index(op.f('ix_event_subscriptions_event_type'), table_name='event_subscriptions')
    op.drop_index(op.f('ix_event_subscriptions_connection_id'), table_name='event_subscriptions')
    op.drop_index(op.f('ix_event_subscriptions_user_id'), table_name='event_subscriptions')
    op.drop_index(op.f('ix_event_subscriptions_subscription_id'), table_name='event_subscriptions')
    op.drop_index('idx_subscriptions_expires', table_name='event_subscriptions')
    op.drop_index('idx_subscriptions_type_active', table_name='event_subscriptions')
    op.drop_index('idx_subscriptions_connection_active', table_name='event_subscriptions')
    op.drop_index('idx_subscriptions_user_active', table_name='event_subscriptions')
    op.drop_table('event_subscriptions')
    
    # Drop events table
    op.drop_index(op.f('ix_events_created_at'), table_name='events')
    op.drop_index(op.f('ix_events_is_processed'), table_name='events')
    op.drop_index(op.f('ix_events_session_id'), table_name='events')
    op.drop_index(op.f('ix_events_user_id'), table_name='events')
    op.drop_index(op.f('ix_events_event_category'), table_name='events')
    op.drop_index(op.f('ix_events_event_type'), table_name='events')
    op.drop_index(op.f('ix_events_event_id'), table_name='events')
    op.drop_index('idx_events_processed', table_name='events')
    op.drop_index('idx_events_severity_created', table_name='events')
    op.drop_index('idx_events_user_created', table_name='events')
    op.drop_index('idx_events_category_created', table_name='events')
    op.drop_index('idx_events_type_created', table_name='events')
    op.drop_table('events')