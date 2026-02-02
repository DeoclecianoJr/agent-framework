"""change_embedding_dimensions_to_384

Revision ID: 78a9f56c09ef
Revises: 
Create Date: 2026-01-30 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '78a9f56c09ef'
down_revision: Union[str, None] = 'ac7f27ba03af'  # Previous migration
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Change embedding column from Vector(1536) to Vector(384) for all-MiniLM-L6-v2 model."""
    # Step 1: Drop existing embeddings (incompatible dimensions)
    op.execute("UPDATE knowledge_documents SET embedding = NULL")
    
    # Step 2: Alter column type to Vector(384)
    op.alter_column('knowledge_documents', 'embedding',
                    existing_type=sa.VARCHAR(),
                    type_=Vector(384),
                    existing_nullable=True)


def downgrade() -> None:
    """Revert embedding column back to Vector(1536)."""
    # Step 1: Drop existing embeddings (incompatible dimensions)
    op.execute("UPDATE knowledge_documents SET embedding = NULL")
    
    # Step 2: Alter column type back to Vector(1536)
    op.alter_column('knowledge_documents', 'embedding',
                    existing_type=sa.VARCHAR(),
                    type_=Vector(1536),
                    existing_nullable=True)
