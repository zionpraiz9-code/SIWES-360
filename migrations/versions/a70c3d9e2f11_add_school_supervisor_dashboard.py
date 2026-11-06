"""Add school supervisor role and academic profile fields."""

from alembic import op
import sqlalchemy as sa


revision = "a70c3d9e2f11"
down_revision = "5b73d9a1c640"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_role", type_="check")
        batch_op.create_check_constraint(
            "ck_users_role",
            "role IN ('student', 'supervisor', 'industry_supervisor', "
            "'university_supervisor', 'school_supervisor', 'admin')",
        )

    with op.batch_alter_table("student_profiles") as batch_op:
        batch_op.add_column(sa.Column("school_supervisor_email", sa.String(length=120)))
        batch_op.add_column(
            sa.Column(
                "academic_score",
                sa.Float(),
                server_default=sa.text("0.0"),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column("school_supervisor_comment", sa.Text(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("student_profiles") as batch_op:
        batch_op.drop_column("school_supervisor_comment")
        batch_op.drop_column("academic_score")
        batch_op.drop_column("school_supervisor_email")

    op.execute(
        "UPDATE users SET role = 'university_supervisor' "
        "WHERE role = 'school_supervisor'"
    )
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_role", type_="check")
        batch_op.create_check_constraint(
            "ck_users_role",
            "role IN ('student', 'supervisor', 'industry_supervisor', "
            "'university_supervisor', 'admin')",
        )
