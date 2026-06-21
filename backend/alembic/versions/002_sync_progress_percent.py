"""Add progress_percent column to sync_state."""

from alembic import op
import sqlalchemy as sa

# Human: Alembic revision for live sync/backfill progress tracking in the dashboard.
# Agent: READ by Alembic chain; down_revision links to 001_initial.
revision = "002_sync_progress_percent"
down_revision = "001_initial"
branch_labels = None
depends_on = None


# Human: Add nullable progress_percent so sync worker can publish live completion percentage.
# Agent: WRITES DB schema via op.add_column; failure modes: column already exists aborts migration.
def upgrade() -> None:
    op.add_column("sync_state", sa.Column("progress_percent", sa.Float(), nullable=True))


# Human: Remove progress_percent column (reverse of upgrade).
# Agent: WRITES DB via op.drop_column; failure modes: missing column raises during downgrade.
def downgrade() -> None:
    op.drop_column("sync_state", "progress_percent")
