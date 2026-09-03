"""Add realtime detection and defect tables."""
import sqlalchemy as sa

from alembic import op

revision = "0003_realtime_detections"
down_revision = "0002_authentication"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "detections",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("image_id", sa.String(128), nullable=False),
        sa.Column("line_id", sa.String(64), nullable=False, server_default="line-1"),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("operator", sa.String(64), nullable=False, server_default="mock-operator"),
        sa.Column("result", sa.String(8), nullable=False),
        sa.Column("image_path", sa.String(512), nullable=False),
        sa.Column("thumbnail_path", sa.String(512), nullable=True),
        sa.Column("model_version", sa.String(64), nullable=False, server_default="mock-v1"),
        sa.Column("config_version", sa.String(64), nullable=False, server_default="default-v1"),
        sa.Column("inference_ms", sa.Float(), nullable=False, server_default="0"),
        sa.Column("mes_status", sa.String(32), nullable=False, server_default="not_sent"),
        sa.Column("defect_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("raw_output", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("image_id"),
    )
    op.create_index("ix_detections_image_id", "detections", ["image_id"])
    op.create_index("ix_detections_line_id", "detections", ["line_id"])
    op.create_index("ix_detections_captured_at", "detections", ["captured_at"])
    op.create_index("ix_detections_result", "detections", ["result"])
    op.create_table(
        "defects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("detection_id", sa.Integer(), sa.ForeignKey("detections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("level", sa.String(16), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("bbox", sa.JSON(), nullable=False),
        sa.Column("width_mm", sa.Float(), nullable=True),
        sa.Column("height_mm", sa.Float(), nullable=True),
    )
    op.create_index("ix_defects_detection_id", "defects", ["detection_id"])


def downgrade() -> None:
    op.drop_index("ix_defects_detection_id", table_name="defects")
    op.drop_table("defects")
    op.drop_index("ix_detections_result", table_name="detections")
    op.drop_index("ix_detections_captured_at", table_name="detections")
    op.drop_index("ix_detections_line_id", table_name="detections")
    op.drop_index("ix_detections_image_id", table_name="detections")
    op.drop_table("detections")
