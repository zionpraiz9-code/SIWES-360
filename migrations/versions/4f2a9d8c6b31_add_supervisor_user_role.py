"""Allow supervisor user role."""

from alembic import op
import sqlalchemy as sa


revision = "4f2a9d8c6b31"
down_revision = "8d1c5a7f2e90"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_role", type_="check")
        batch_op.create_check_constraint(
            "ck_users_role",
            "role IN ('student', 'supervisor', 'industry_supervisor', "
            "'university_supervisor', 'admin')",
        )


def downgrade():
    op.execute(
        "UPDATE users SET role = 'industry_supervisor' WHERE role = 'supervisor'"
    )
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("ck_users_role", type_="check")
        batch_op.create_check_constraint(
            "ck_users_role",
            "role IN ('student', 'industry_supervisor', "
            "'university_supervisor', 'admin')",
        )
