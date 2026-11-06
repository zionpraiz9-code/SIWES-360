"""Support daily log rejection and supervisor comments."""

from alembic import op
import sqlalchemy as sa


revision = "6c91e4b7a205"
down_revision = "2a7c9e5d1b40"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("daily_logs") as batch_op:
        batch_op.drop_constraint("ck_daily_logs_status", type_="check")
        batch_op.add_column(sa.Column("supervisor_comment", sa.Text(), nullable=True))

    op.execute(
        sa.text(
            "UPDATE daily_logs SET status = CASE "
            "WHEN lower(status) = 'approved' THEN 'Approved' "
            "WHEN lower(status) = 'rejected' THEN 'Rejected' "
            "ELSE 'Pending' END"
        )
    )
    op.execute(
        sa.text(
            "UPDATE daily_logs SET supervisor_comment = supervisor_feedback "
            "WHERE supervisor_feedback IS NOT NULL"
        )
    )

    with op.batch_alter_table("daily_logs") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=16),
            server_default="Pending",
            existing_nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_daily_logs_status",
            "status IN ('Pending', 'Approved', 'Rejected')",
        )


def downgrade():
    with op.batch_alter_table("daily_logs") as batch_op:
        batch_op.drop_constraint("ck_daily_logs_status", type_="check")

    op.execute(
        sa.text(
            "UPDATE daily_logs SET status = CASE "
            "WHEN status = 'Approved' THEN 'approved' "
            "ELSE 'pending' END"
        )
    )

    with op.batch_alter_table("daily_logs") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=16),
            server_default="pending",
            existing_nullable=False,
        )
        batch_op.drop_column("supervisor_comment")
        batch_op.create_check_constraint(
            "ck_daily_logs_status",
            "status IN ('pending', 'approved')",
        )
