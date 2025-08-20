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
down_revision = 'previous_revision'  # Replace with actual previous revision
branch_labels = None
depends_on = None


def upgrade():
    # Add new columns to forwarders table
    op.add_column('forwarders', sa.Column('priority', sa.Integer(), nullable=False, server_default='5'))
    op.add_column('forwarders', sa.Column('group_name', sa.String(length=100), nullable=True))
    op.add_column('forwarders', sa.Column('group_priority', sa.Integer(), nullable=False, server_default='5'))
    op.add_column('forwarders', sa.Column('is_template', sa.Boolean(), nullable=False, server_default='false'))
    op.add_column('forwarders', sa.Column('template_name', sa.String(length=255), nullable=True))
    op.add_column('forwarders', sa.Column('created_from_template', sa.String(length=255), nullable=True))
    
    # Add check constraints for forwarders table
    op.create_check_constraint('check_priority_range', 'forwarders', 'priority >= 1 AND priority <= 10')
    op.create_check_constraint('check_group_priority_range', 'forwarders', 'group_priority >= 1 AND group_priority <= 10')
    op.create_check_constraint('check_group_name_not_empty', 'forwarders', 'group_name IS NULL OR length(group_name) >= 1')
    op.create_check_constraint('check_template_name_not_empty', 'forwarders', 'template_name IS NULL OR length(template_name) >= 1')
    op.create_check_constraint('check_created_from_template_not_empty', 'forwarders', 'created_from_template IS NULL OR length(created_from_template) >= 1')
    op.create_check_constraint('check_template_has_name', 'forwarders', 'NOT (is_template = true AND template_name IS NULL)')
    
    # Create forwarder_templates table
    op.create_table('forwarder_templates',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('forwarder_type', sa.String(length=20), nullable=False),
        sa.Column('default_domains', sa.JSON(), nullable=True),
        sa.Column('default_servers', sa.JSON(), nullable=True),
        sa.Column('default_priority', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('default_group_name', sa.String(length=100), nullable=True),
        sa.Column('default_health_check_enabled', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('is_system_template', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('usage_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_by', sa.Integer(), nullable=True),
        sa.Column('updated_by', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint("forwarder_type IN ('active_directory', 'intranet', 'public')", name='check_template_forwarder_type'),
        sa.CheckConstraint('length(name) >= 1', name='check_template_name_not_empty'),
        sa.CheckConstraint('default_priority >= 1 AND default_priority <= 10', name='check_template_priority_range'),
        sa.CheckConstraint('default_group_name IS NULL OR length(default_group_name) >= 1', name='check_template_group_name_not_empty'),
        sa.CheckConstraint('usage_count >= 0', name='check_template_usage_count_non_negative'),
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
    
    # Drop check constraints from forwarders table
    op.drop_constraint('check_template_has_name', 'forwarders', type_='check')
    op.drop_constraint('check_created_from_template_not_empty', 'forwarders', type_='check')
    op.drop_constraint('check_template_name_not_empty', 'forwarders', type_='check')
    op.drop_constraint('check_group_name_not_empty', 'forwarders', type_='check')
    op.drop_constraint('check_group_priority_range', 'forwarders', type_='check')
    op.drop_constraint('check_priority_range', 'forwarders', type_='check')
    
    # Drop columns from forwarders table
    op.drop_column('forwarders', 'created_from_template')
    op.drop_column('forwarders', 'template_name')
    op.drop_column('forwarders', 'is_template')
    op.drop_column('forwarders', 'group_priority')
    op.drop_column('forwarders', 'group_name')
    op.drop_column('forwarders', 'priority')