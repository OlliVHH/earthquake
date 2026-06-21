"""Initial schema for earthquakes and sync_state."""

from alembic import op
import sqlalchemy as sa

revision = "001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "earthquakes",
        sa.Column("event_id", sa.String(length=64), nullable=False),
        sa.Column("time_utc", sa.DateTime(), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("depth_km", sa.Float(), nullable=False),
        sa.Column("magnitude", sa.Float(), nullable=True),
        sa.Column("mag_type", sa.String(length=16), nullable=True),
        sa.Column("location_name", sa.String(length=512), nullable=True),
        sa.Column("author", sa.String(length=64), nullable=True),
        sa.Column("catalog", sa.String(length=64), nullable=True),
        sa.Column("contributor", sa.String(length=64), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("event_id"),
    )
    op.create_index("ix_earthquakes_time_utc", "earthquakes", ["time_utc"])
    op.create_index("ix_earthquakes_magnitude", "earthquakes", ["magnitude"])
    op.create_index("ix_earthquakes_location_name", "earthquakes", ["location_name"])
    op.create_index("ix_earthquakes_lat_lon", "earthquakes", ["latitude", "longitude"])

    op.create_table(
        "sync_state",
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("last_updatedafter", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("key"),
    )


def downgrade() -> None:
    op.drop_table("sync_state")
    op.drop_table("earthquakes")
