"""Persist pipeline sessions and their owners.

Revision ID: 20261108_live
Revises: fe56fa70289e
"""

from alembic import op
import sqlalchemy as sa

revision = "20261108_live"
down_revision = "fe56fa70289e"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("pipeline_run", sa.Column("id", sa.String(12), primary_key=True), sa.Column("owner_id", sa.Uuid(), sa.ForeignKey("user.id", ondelete="CASCADE"), nullable=False), sa.Column("started_at", sa.Float(), nullable=False), sa.Column("status", sa.String(32), nullable=False), sa.Column("payload", sa.JSON(), nullable=False))
    for column in ("owner_id", "started_at", "status"):
        op.create_index(f"ix_pipeline_run_{column}", "pipeline_run", [column])


def downgrade():
    op.drop_table("pipeline_run")
