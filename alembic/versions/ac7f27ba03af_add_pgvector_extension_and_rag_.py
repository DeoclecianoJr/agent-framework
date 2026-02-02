"""Add pgvector extension and RAG knowledge tables

Revision ID: ac7f27ba03af
Revises: 2377a2024ac8
Create Date: 2026-01-27 18:30:50.436003

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = 'ac7f27ba03af'
down_revision: Union[str, Sequence[str], None] = '2377a2024ac8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Enable pgvector extension
    op.execute('CREATE EXTENSION IF NOT EXISTS vector')
    
    # Create knowledge_documents table
    op.create_table(
        'knowledge_documents',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agent_id', sa.String(255), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('source_type', sa.String(50), nullable=False, index=True),
        sa.Column('source_id', sa.String(255), nullable=False, index=True),
        sa.Column('file_name', sa.String(500), nullable=False),
        sa.Column('content_chunk', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('embedding', Vector(1536), nullable=True),
        sa.Column('attrs', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now())
    )
    
    # Note: IVFFlat index creation requires data in table for training
    # Creating a placeholder index for now, or skip if table is empty
    # In production, create index after initial data load:
    # CREATE INDEX idx_kd_embedding_ivfflat ON knowledge_documents 
    # USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
    
    # Create knowledge_sources table
    op.create_table(
        'knowledge_sources',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('agent_id', sa.String(255), sa.ForeignKey('agents.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('config', sa.JSON(), nullable=False, server_default='{}'),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sync_status', sa.String(50), nullable=False, server_default="'pending'"),
        sa.Column('sync_errors', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now())
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('knowledge_sources')
    op.drop_table('knowledge_documents')
    op.execute('DROP EXTENSION IF EXISTS vector')

