"""Add configuration draft, immutable versions, and detection snapshots."""

from alembic import op
import sqlalchemy as sa

revision = "0007_configuration_versions"
down_revision = "0006_analytics_aggregates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "configuration_state",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("draft_payload", sa.JSON(), nullable=False),
        sa.Column("draft_revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("published_version", sa.String(64), nullable=True),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
    )
    op.create_table(
        "config_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("published_by", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.UniqueConstraint("version", name="uq_config_versions_version"),
    )
    op.create_index("ix_config_versions_version", "config_versions", ["version"])
    op.create_index("ix_config_versions_published_at", "config_versions", ["published_at"])
    op.create_table(
        "config_publish_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("idempotency_key", sa.String(128), nullable=False),
        sa.Column("config_version", sa.String(64), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_config_publish_keys_key"),
    )
    op.create_index("ix_config_publish_keys_idempotency_key", "config_publish_keys", ["idempotency_key"])
    op.add_column("detections", sa.Column("config_snapshot", sa.JSON(), nullable=True))
    op.add_column("audit_logs", sa.Column("config_version", sa.String(64), nullable=True))
    op.create_index("ix_audit_logs_config_version", "audit_logs", ["config_version"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_config_version", table_name="audit_logs")
    op.drop_column("audit_logs", "config_version")
    op.drop_column("detections", "config_snapshot")
    op.drop_index("ix_config_publish_keys_idempotency_key", table_name="config_publish_keys")
    op.drop_table("config_publish_keys")
    op.drop_index("ix_config_versions_published_at", table_name="config_versions")
    op.drop_index("ix_config_versions_version", table_name="config_versions")
    op.drop_table("config_versions")
    op.drop_table("configuration_state")
