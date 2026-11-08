"""Recoverable history deletion, retaining trace files and restart tombstones.

Revision ID: 20261108_trash
Revises: 20261108_local
"""

from alembic import op
import sqlalchemy as sa

revision = "20261108_trash"
down_revision = "20261108_local"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("pipeline_run", sa.Column("deleted_at", sa.Float(), nullable=True))
    op.create_index("ix_pipeline_run_deleted_at", "pipeline_run", ["deleted_at"])


def downgrade():
    op.drop_index("ix_pipeline_run_deleted_at", table_name="pipeline_run")
    op.drop_column("pipeline_run", "deleted_at")
