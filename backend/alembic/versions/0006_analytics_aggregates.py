"""Add hourly analytics aggregates and heatmap buckets."""

import sqlalchemy as sa

from alembic import op

revision = "0006_analytics_aggregates"
down_revision = "0005_history_fr_completion"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analytics_hourly_aggregates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("line_id", sa.String(64), nullable=False),
        sa.Column("total_detections", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("ng_detections", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scratch_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pitted_surface_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scratch_minor_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("scratch_severe_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pitted_surface_minor_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("pitted_surface_severe_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("bucket_start", "line_id", name="uq_analytics_hour_line"),
    )
    op.create_index("ix_analytics_hour_bucket_start", "analytics_hourly_aggregates", ["bucket_start"])
    op.create_index("ix_analytics_hour_line_id", "analytics_hourly_aggregates", ["line_id"])
    op.create_table(
        "analytics_heatmap_hourly_buckets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("bucket_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("line_id", sa.String(64), nullable=False),
        sa.Column("angle_bucket", sa.Integer(), nullable=False),
        sa.Column("axial_bucket", sa.Integer(), nullable=False),
        sa.Column("defect_count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("bucket_start", "line_id", "angle_bucket", "axial_bucket", name="uq_heatmap_hour_cell"),
    )
    op.create_index("ix_heatmap_hour_bucket_start", "analytics_heatmap_hourly_buckets", ["bucket_start"])
    op.create_index("ix_heatmap_hour_line_id", "analytics_heatmap_hourly_buckets", ["line_id"])


def downgrade() -> None:
    op.drop_index("ix_heatmap_hour_line_id", table_name="analytics_heatmap_hourly_buckets")
    op.drop_index("ix_heatmap_hour_bucket_start", table_name="analytics_heatmap_hourly_buckets")
    op.drop_table("analytics_heatmap_hourly_buckets")
    op.drop_index("ix_analytics_hour_line_id", table_name="analytics_hourly_aggregates")
    op.drop_index("ix_analytics_hour_bucket_start", table_name="analytics_hourly_aggregates")
    op.drop_table("analytics_hourly_aggregates")
