"""Expand daily logs for the digital logbook."""

from alembic import op
import sqlalchemy as sa


revision = "3c82e91b4a17"
down_revision = "9a41e7d2c630"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "daily_logs",
        sa.Column("tools_used", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "daily_logs",
        sa.Column("skills_learned", sa.Text(), server_default="", nullable=False),
    )
    op.add_column(
        "daily_logs",
        sa.Column(
            "challenges_encountered",
            sa.Text(),
            server_default="",
            nullable=False,
        ),
    )
    op.add_column(
        "daily_logs",
        sa.Column(
            "status",
            sa.String(length=16),
            server_default="pending",
            nullable=False,
        ),
    )
    op.execute(
        sa.text(
            "UPDATE daily_logs SET status = 'approved' "
            "WHERE supervisor_feedback IS NOT NULL"
        )
    )
    with op.batch_alter_table("daily_logs") as batch_op:
        batch_op.create_check_constraint(
            "ck_daily_logs_status",
            "status IN ('pending', 'approved')",
        )


def downgrade():
    with op.batch_alter_table("daily_logs") as batch_op:
        batch_op.drop_constraint("ck_daily_logs_status", type_="check")
        batch_op.drop_column("status")
        batch_op.drop_column("challenges_encountered")
        batch_op.drop_column("skills_learned")
        batch_op.drop_column("tools_used")
