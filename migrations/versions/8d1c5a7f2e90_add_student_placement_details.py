"""Add industrial placement details to student profiles."""

from alembic import op
import sqlalchemy as sa


revision = "8d1c5a7f2e90"
down_revision = "71e4a6c2d903"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("student_profiles") as batch_op:
        batch_op.alter_column(
            "placement_start_date",
            new_column_name="start_date",
            existing_type=sa.Date(),
            existing_nullable=True,
        )
        batch_op.add_column(sa.Column("company_name", sa.String(length=160)))
        batch_op.add_column(sa.Column("company_address", sa.Text()))
        batch_op.add_column(sa.Column("supervisor_name", sa.String(length=120)))
        batch_op.add_column(sa.Column("supervisor_email", sa.String(length=255)))
        batch_op.add_column(sa.Column("supervisor_phone", sa.String(length=32)))
        batch_op.add_column(sa.Column("end_date", sa.Date()))


def downgrade():
    with op.batch_alter_table("student_profiles") as batch_op:
        batch_op.drop_column("end_date")
        batch_op.drop_column("supervisor_phone")
        batch_op.drop_column("supervisor_email")
        batch_op.drop_column("supervisor_name")
        batch_op.drop_column("company_address")
        batch_op.drop_column("company_name")
        batch_op.alter_column(
            "start_date",
            new_column_name="placement_start_date",
            existing_type=sa.Date(),
            existing_nullable=True,
        )
