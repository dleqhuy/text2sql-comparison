"""Make pipeline history independent of accounts without losing existing runs.

Revision ID: 20261108_local
Revises: 20261108_live
"""
from alembic import op
import sqlalchemy as sa

revision = "20261108_local"
down_revision = "20261108_live"
branch_labels = None
depends_on = None

def upgrade():
    op.drop_column("pipeline_run", "owner_id")
    op.execute("UPDATE pipeline_run SET payload = (payload::jsonb - 'owner_id')::json")

def downgrade():
    # Historical ownership cannot be reconstructed after switching to shared history.
    op.add_column("pipeline_run", sa.Column("owner_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("pipeline_run_owner_id_fkey", "pipeline_run", "user", ["owner_id"], ["id"], ondelete="CASCADE")
    op.create_index("ix_pipeline_run_owner_id", "pipeline_run", ["owner_id"])
