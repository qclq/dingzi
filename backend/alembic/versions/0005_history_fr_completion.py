"""Complete history filters and MES work-order association."""

import sqlalchemy as sa

from alembic import op

revision = "0005_history_fr_completion"
down_revision = "0004_history_exports"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("detections", sa.Column("mes_work_order", sa.String(128), nullable=True))
    op.create_index("ix_detections_operator", "detections", ["operator"])


def downgrade() -> None:
    op.drop_index("ix_detections_operator", table_name="detections")
    op.drop_column("detections", "mes_work_order")
