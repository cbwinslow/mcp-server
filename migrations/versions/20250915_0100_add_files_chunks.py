"""add files and chunks tables

Revision ID: 20250915_0100
Revises: 20250915_0001
Create Date: 2025-09-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = '20250915_0100'
down_revision = '20250915_0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'files',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('repository_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('repositories.id'), nullable=True),
        sa.Column('path', sa.String(), nullable=False),
        sa.Column('size', sa.Integer(), nullable=True),
        sa.Column('sha256', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        'chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('file_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('files.id'), nullable=True),
        sa.Column('index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('chunks')
    op.drop_table('files')

