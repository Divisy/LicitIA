"""add_support_tickets_table

Revision ID: b2ac5ee85b1a
Revises: 0e227d9a6d90
Create Date: 2025-12-01 05:51:24.362944

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = 'b2ac5ee85b1a'
down_revision = '0e227d9a6d90'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create ENUM types (checkfirst will skip if they already exist)
    ticket_category_enum = postgresql.ENUM('TECHNICAL', 'BILLING', 'FEATURE_REQUEST', 'BUG_REPORT', 'GENERAL', 'OTHER', name='ticketcategory', create_type=False)
    ticket_priority_enum = postgresql.ENUM('LOW', 'MEDIUM', 'HIGH', 'URGENT', name='ticketpriority', create_type=False)
    ticket_status_enum = postgresql.ENUM('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED', name='ticketstatus', create_type=False)
    
    # Create types only if they don't exist
    conn = op.get_bind()
    conn.execute(sa.text("DO $$ BEGIN CREATE TYPE ticketcategory AS ENUM ('TECHNICAL', 'BILLING', 'FEATURE_REQUEST', 'BUG_REPORT', 'GENERAL', 'OTHER'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))
    conn.execute(sa.text("DO $$ BEGIN CREATE TYPE ticketpriority AS ENUM ('LOW', 'MEDIUM', 'HIGH', 'URGENT'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))
    conn.execute(sa.text("DO $$ BEGIN CREATE TYPE ticketstatus AS ENUM ('OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED'); EXCEPTION WHEN duplicate_object THEN null; END $$;"))
    conn.commit()
    
    # Create table
    op.create_table('support_tickets',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=True),
    sa.Column('company', sa.String(length=255), nullable=True),
    sa.Column('subject', sa.String(length=500), nullable=False),
    sa.Column('message', sa.Text(), nullable=False),
    sa.Column('category', ticket_category_enum, nullable=False),
    sa.Column('priority', ticket_priority_enum, nullable=False),
    sa.Column('status', ticket_status_enum, nullable=False),
    sa.Column('ticket_number', sa.String(length=50), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('updated_at', sa.DateTime(), nullable=False),
    sa.Column('resolved_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_support_tickets_email'), 'support_tickets', ['email'], unique=False)
    op.create_index(op.f('ix_support_tickets_id'), 'support_tickets', ['id'], unique=False)
    op.create_index(op.f('ix_support_tickets_ticket_number'), 'support_tickets', ['ticket_number'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_support_tickets_ticket_number'), table_name='support_tickets')
    op.drop_index(op.f('ix_support_tickets_id'), table_name='support_tickets')
    op.drop_index(op.f('ix_support_tickets_email'), table_name='support_tickets')
    op.drop_table('support_tickets')
    
    # Drop ENUM types
    sa.Enum(name='ticketstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='ticketpriority').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='ticketcategory').drop(op.get_bind(), checkfirst=True)

