"""add_feedback_table

Revision ID: b42030ef19cc
Revises: b2ac5ee85b1a
Create Date: 2025-12-01 06:05:13.706263

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b42030ef19cc'
down_revision = 'b2ac5ee85b1a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ENUM types (using DO block to handle if they already exist)
    conn = op.get_bind()
    conn.execute(sa.text("DO $$ BEGIN CREATE TYPE feedbacktype AS ENUM ('NPS', 'FEATURE_REQUEST', 'BUG_REPORT', 'GENERAL', 'USABILITY'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))
    conn.execute(sa.text("DO $$ BEGIN CREATE TYPE feedbackstatus AS ENUM ('NEW', 'REVIEWED', 'IMPLEMENTED', 'REJECTED'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))
    
    # Create table
    op.create_table('feedback',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=True),
    sa.Column('company', sa.String(length=255), nullable=True),
    sa.Column('type', postgresql.ENUM('NPS', 'FEATURE_REQUEST', 'BUG_REPORT', 'GENERAL', 'USABILITY', name='feedbacktype', create_type=False), nullable=False),
    sa.Column('score', sa.Integer(), nullable=True),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('context', sa.Text(), nullable=True),
    sa.Column('status', postgresql.ENUM('NEW', 'REVIEWED', 'IMPLEMENTED', 'REJECTED', name='feedbackstatus', create_type=False), nullable=False, server_default='NEW'),
    sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_feedback_email'), 'feedback', ['email'], unique=False)
    op.create_index(op.f('ix_feedback_id'), 'feedback', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_feedback_id'), table_name='feedback')
    op.drop_index(op.f('ix_feedback_email'), table_name='feedback')
    op.drop_table('feedback')
    
    # Drop ENUM types
    sa.Enum(name='feedbackstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='feedbacktype').drop(op.get_bind(), checkfirst=True)

