"""Add export jobs and history query index."""

import sqlalchemy as sa

from alembic import op

revision = "0004_history_exports"
down_revision = "0003_realtime_detections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_detections_result_captured_id", "detections", ["result", "captured_at", "id"]
    )
    op.create_table(
        "export_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("format", sa.String(8), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="queued"),
        sa.Column("query", sa.JSON(), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_path", sa.String(512), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_export_jobs_created_by_id", "export_jobs", ["created_by_id"])
    op.create_index("ix_export_jobs_status", "export_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_export_jobs_status", table_name="export_jobs")
    op.drop_index("ix_export_jobs_created_by_id", table_name="export_jobs")
    op.drop_table("export_jobs")
    op.drop_index("ix_detections_result_captured_id", table_name="detections")
