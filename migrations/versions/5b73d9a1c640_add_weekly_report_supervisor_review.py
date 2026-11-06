"""Add weekly report approval and supervisor comments."""

from alembic import op
import sqlalchemy as sa


revision = "5b73d9a1c640"
down_revision = "6c91e4b7a205"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("weekly_reports") as batch_op:
        batch_op.drop_constraint("ck_weekly_reports_status", type_="check")
        batch_op.add_column(sa.Column("supervisor_comment", sa.Text(), nullable=True))

    op.execute(
        sa.text(
            "UPDATE weekly_reports SET status = CASE "
            "WHEN lower(status) = 'reviewed' THEN 'Approved' "
            "ELSE 'Pending' END"
        )
    )
    op.execute(
        sa.text(
            "UPDATE weekly_reports SET supervisor_comment = supervisor_feedback "
            "WHERE supervisor_feedback IS NOT NULL"
        )
    )

    with op.batch_alter_table("weekly_reports") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=16),
            server_default="Pending",
            existing_nullable=False,
        )
        batch_op.create_check_constraint(
            "ck_weekly_reports_status",
            "status IN ('Pending', 'Approved', 'Rejected')",
        )


def downgrade():
    with op.batch_alter_table("weekly_reports") as batch_op:
        batch_op.drop_constraint("ck_weekly_reports_status", type_="check")

    op.execute(
        sa.text(
            "UPDATE weekly_reports SET status = CASE "
            "WHEN status = 'Approved' THEN 'reviewed' "
            "ELSE 'submitted' END"
        )
    )

    with op.batch_alter_table("weekly_reports") as batch_op:
        batch_op.alter_column(
            "status",
            existing_type=sa.String(length=16),
            server_default="submitted",
            existing_nullable=False,
        )
        batch_op.drop_column("supervisor_comment")
        batch_op.create_check_constraint(
            "ck_weekly_reports_status",
            "status IN ('submitted', 'reviewed')",
        )
