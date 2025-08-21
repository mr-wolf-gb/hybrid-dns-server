"""Add forwarder priority management, grouping, and templates

Revision ID: add_forwarder_priority_grouping_templates
Revises: previous_revision
Create Date: 2024-01-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_forwarder_priority_grouping_templates'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to forwarders table using batch mode for SQLite compatibility
    with op.batch_alter_table('forwarders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('priority', sa.Integer(), nullable=False, server_default='5'))
        batch_op.add_column(sa.Column('group_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('group_priority', sa.Integer(), nullable=False, server_default='5'))
        batch_op.add_column(sa.Column('is_template', sa.Boolean(), nullable=False, server_default='false'))
        batch_op.add_column(sa.Column('template_name', sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column('created_from_template', sa.String(length=255), nullable=True))
    
    # Create forwarder_templates table (SQLite compatible)
    op.create_table('forwarder_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('forwarder_type', sa.String(length=20), nullable=False),
        sa.Column('default_domains', sa.Text(), nullable=True),  # Use Text instead of JSON for SQLite
        sa.Column('default_servers', sa.Text(), nullable=True),  # Use Text instead of JSON for SQLite
        sa.Column('default_priority', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('default_group_name', sa.String(length=100), nullable=True),
        sa.Column('default_health_check_enabled', sa.Boolean(), nullable=False, server_default='1'),  # Use '1' for SQLite
        sa.Column('is_system_template', sa.Boolean(), nullable=False, server_default='0'),  # Use '0' for SQLite
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),  # SQLite compatible
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),  # SQLite compatible
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['updated_by'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # Create indexes for forwarders table
    op.create_index('idx_forwarders_priority', 'forwarders', ['priority'])
    op.create_index('idx_forwarders_group_name', 'forwarders', ['group_name'])
    op.create_index('idx_forwarders_group_priority', 'forwarders', ['group_name', 'group_priority'])
    op.create_index('idx_forwarders_is_template', 'forwarders', ['is_template'])
    op.create_index('idx_forwarders_template_name', 'forwarders', ['template_name'])
    op.create_index('idx_forwarders_created_from_template', 'forwarders', ['created_from_template'])
    
    # Create indexes for forwarder_templates table
    op.create_index('idx_forwarder_templates_name', 'forwarder_templates', ['name'])
    op.create_index('idx_forwarder_templates_type', 'forwarder_templates', ['forwarder_type'])
    op.create_index('idx_forwarder_templates_system', 'forwarder_templates', ['is_system_template'])
    op.create_index('idx_forwarder_templates_usage', 'forwarder_templates', ['usage_count'])
    op.create_index('idx_forwarder_templates_created_by', 'forwarder_templates', ['created_by'])


def downgrade():
    # Drop indexes for forwarder_templates table
    op.drop_index('idx_forwarder_templates_created_by', table_name='forwarder_templates')
    op.drop_index('idx_forwarder_templates_usage', table_name='forwarder_templates')
    op.drop_index('idx_forwarder_templates_system', table_name='forwarder_templates')
    op.drop_index('idx_forwarder_templates_type', table_name='forwarder_templates')
    op.drop_index('idx_forwarder_templates_name', table_name='forwarder_templates')
    
    # Drop indexes for forwarders table
    op.drop_index('idx_forwarders_created_from_template', table_name='forwarders')
    op.drop_index('idx_forwarders_template_name', table_name='forwarders')
    op.drop_index('idx_forwarders_is_template', table_name='forwarders')
    op.drop_index('idx_forwarders_group_priority', table_name='forwarders')
    op.drop_index('idx_forwarders_group_name', table_name='forwarders')
    op.drop_index('idx_forwarders_priority', table_name='forwarders')
    
    # Drop forwarder_templates table
    op.drop_table('forwarder_templates')
    
    # Drop columns from forwarders table using batch mode for SQLite compatibility
    with op.batch_alter_table('forwarders', schema=None) as batch_op:
        batch_op.drop_column('created_from_template')
        batch_op.drop_column('template_name')
        batch_op.drop_column('is_template')
        batch_op.drop_column('group_priority')
        batch_op.drop_column('group_name')
        batch_op.drop_column('priority')