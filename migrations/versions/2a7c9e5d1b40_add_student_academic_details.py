"""Add student matric number and department."""

from alembic import op
import sqlalchemy as sa


revision = "2a7c9e5d1b40"
down_revision = "4f2a9d8c6b31"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("student_profiles") as batch_op:
        batch_op.add_column(sa.Column("matric_number", sa.String(length=64)))
        batch_op.add_column(sa.Column("department", sa.String(length=160)))


def downgrade():
    with op.batch_alter_table("student_profiles") as batch_op:
        batch_op.drop_column("department")
        batch_op.drop_column("matric_number")
