"""Add Phase 7 system management storage."""

from alembic import op
import sqlalchemy as sa

revision = "0008_system_management"
down_revision = "0007_configuration_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("users", sa.Column("credential_version", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("users", sa.Column("revision", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("audit_logs", sa.Column("level", sa.String(16), nullable=False, server_default="INFO"))
    op.add_column("audit_logs", sa.Column("source", sa.String(64), nullable=False, server_default="system"))
    op.add_column("audit_logs", sa.Column("message", sa.String(512), nullable=True))
    op.create_index("ix_audit_logs_level", "audit_logs", ["level"])
    op.create_index("ix_audit_logs_source", "audit_logs", ["source"])
    op.create_table("system_logs", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("level", sa.String(16), nullable=False), sa.Column("source", sa.String(64), nullable=False), sa.Column("message", sa.Text(), nullable=False), sa.Column("context", sa.JSON(), nullable=True), sa.Column("trace_id", sa.String(64), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))
    op.create_index("ix_system_logs_created_at", "system_logs", ["created_at"])
    op.create_index("ix_system_logs_level", "system_logs", ["level"])
    op.create_index("ix_system_logs_source", "system_logs", ["source"])
    op.create_table("system_settings", sa.Column("key", sa.String(64), primary_key=True), sa.Column("value", sa.JSON(), nullable=False), sa.Column("revision", sa.Integer(), nullable=False, server_default="1"), sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))
    op.create_table("mes_deliveries", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("detection_id", sa.Integer(), sa.ForeignKey("detections.id", ondelete="CASCADE"), nullable=False), sa.Column("idempotency_key", sa.String(128), nullable=False), sa.Column("payload", sa.JSON(), nullable=False), sa.Column("status", sa.String(24), nullable=False, server_default="pending"), sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"), sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True), sa.Column("last_status_code", sa.Integer(), nullable=True), sa.Column("last_error", sa.Text(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True), sa.UniqueConstraint("detection_id", name="uq_mes_deliveries_detection"), sa.UniqueConstraint("idempotency_key", name="uq_mes_deliveries_key"))
    op.create_index("ix_mes_deliveries_detection_id", "mes_deliveries", ["detection_id"])
    op.create_index("ix_mes_deliveries_status", "mes_deliveries", ["status"])
    op.create_index("ix_mes_deliveries_next_attempt_at", "mes_deliveries", ["next_attempt_at"])
    op.create_table("detection_files", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("detection_id", sa.Integer(), sa.ForeignKey("detections.id", ondelete="CASCADE"), nullable=False), sa.Column("kind", sa.String(32), nullable=False, server_default="image"), sa.Column("uri", sa.String(512), nullable=False), sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"), sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True), sa.Column("delete_reason", sa.String(32), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True))
    op.create_index("ix_detection_files_detection_id", "detection_files", ["detection_id"])
    op.create_index("ix_detection_files_deleted_at", "detection_files", ["deleted_at"])
    op.create_index("ix_detection_files_created_at", "detection_files", ["created_at"])
    op.create_table("password_reset_requests", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("token_hash", sa.String(64), nullable=False), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False), sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True), sa.UniqueConstraint("token_hash"))
    op.create_index("ix_password_reset_requests_user_id", "password_reset_requests", ["user_id"])
    op.create_index("ix_password_reset_requests_expires_at", "password_reset_requests", ["expires_at"])


def downgrade() -> None:
    for name, table in (("ix_password_reset_requests_expires_at", "password_reset_requests"), ("ix_password_reset_requests_user_id", "password_reset_requests")): op.drop_index(name, table_name=table)
    op.drop_table("password_reset_requests")
    for name in ("ix_detection_files_created_at", "ix_detection_files_deleted_at", "ix_detection_files_detection_id"): op.drop_index(name, table_name="detection_files")
    op.drop_table("detection_files")
    for name in ("ix_mes_deliveries_next_attempt_at", "ix_mes_deliveries_status", "ix_mes_deliveries_detection_id"): op.drop_index(name, table_name="mes_deliveries")
    op.drop_table("mes_deliveries")
    op.drop_table("system_settings")
    for name in ("ix_system_logs_source", "ix_system_logs_level", "ix_system_logs_created_at"): op.drop_index(name, table_name="system_logs")
    op.drop_table("system_logs")
    op.drop_index("ix_audit_logs_source", table_name="audit_logs"); op.drop_index("ix_audit_logs_level", table_name="audit_logs")
    op.drop_column("audit_logs", "message"); op.drop_column("audit_logs", "source"); op.drop_column("audit_logs", "level")
    op.drop_column("users", "revision"); op.drop_column("users", "credential_version"); op.drop_column("users", "deleted_at")
