"""Add challenges and plans to weekly reports."""

from alembic import op
import sqlalchemy as sa


revision = "71e4a6c2d903"
down_revision = "3c82e91b4a17"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "weekly_reports",
        sa.Column(
            "challenges_encountered",
            sa.Text(),
            server_default="",
            nullable=False,
        ),
    )
    op.add_column(
        "weekly_reports",
        sa.Column(
            "plans_for_next_week",
            sa.Text(),
            server_default="",
            nullable=False,
        ),
    )


def downgrade():
    op.drop_column("weekly_reports", "plans_for_next_week")
    op.drop_column("weekly_reports", "challenges_encountered")
