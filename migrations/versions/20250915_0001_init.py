from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = '20250915_0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'repositories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('owner', sa.String(), nullable=False),
        sa.Column('url', sa.String(), nullable=False, unique=True),
        sa.Column('description', sa.Text()),
        sa.Column('language', sa.String()),
        sa.Column('stars', sa.Integer(), server_default='0'),
        sa.Column('forks', sa.Integer(), server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True)),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
        sa.Column('added_at', sa.DateTime(timezone=True)),
        sa.Column('processed', sa.Boolean(), server_default=sa.text('false')),
        sa.Column('crawled_at', sa.DateTime(timezone=True)),
        sa.Column('extracted_at', sa.DateTime(timezone=True)),
        sa.Column('embedded_at', sa.DateTime(timezone=True)),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text())),
    )

    op.create_table(
        'crawler_jobs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('job_id', sa.String(), nullable=False, unique=True),
        sa.Column('status', sa.String(), server_default='pending'),
        sa.Column('target', sa.String()),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text())),
        sa.Column('started_at', sa.DateTime(timezone=True)),
        sa.Column('completed_at', sa.DateTime(timezone=True)),
        sa.Column('repositories_found', sa.Integer(), server_default='0'),
        sa.Column('error_message', sa.Text()),
    )

    op.create_table(
        'embeddings',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('repository_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('repositories.id')),
        sa.Column('content_type', sa.String()),
        sa.Column('content_path', sa.String()),
        sa.Column('embedding_vector', sa.Text()),
        sa.Column('model_name', sa.String()),
        sa.Column('generated_at', sa.DateTime(timezone=True)),
    )

    op.create_table(
        'system_status',
        sa.Column('component', sa.String(), primary_key=True),
        sa.Column('status', sa.String(), server_default='idle'),
        sa.Column('last_updated', sa.DateTime(timezone=True)),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text())),
    )


def downgrade() -> None:
    op.drop_table('system_status')
    op.drop_table('embeddings')
    op.drop_table('crawler_jobs')
    op.drop_table('repositories')

