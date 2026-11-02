"""Add student workspace records.

Revision ID: 9a41e7d2c630
Revises: f61cb6ce6fc8
Create Date: 2026-10-31
"""
from alembic import op
import sqlalchemy as sa


revision = "9a41e7d2c630"
down_revision = "f61cb6ce6fc8"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "student_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("placement_start_date", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "daily_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("log_date", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("activities", sa.Text(), nullable=False),
        sa.Column("supervisor_feedback", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_daily_logs_log_date", "daily_logs", ["log_date"])
    op.create_index("ix_daily_logs_user_id", "daily_logs", ["user_id"])
    op.create_table(
        "attendances",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("attendance_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('present', 'absent')",
            name="ck_attendances_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "attendance_date", name="uq_attendance_user_date"),
    )
    op.create_index(
        "ix_attendances_attendance_date",
        "attendances",
        ["attendance_date"],
    )
    op.create_index("ix_attendances_user_id", "attendances", ["user_id"])
    op.create_table(
        "weekly_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("supervisor_feedback", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('submitted', 'reviewed')",
            name="ck_weekly_reports_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "week_start", name="uq_weekly_report_user_week"),
    )
    op.create_index("ix_weekly_reports_user_id", "weekly_reports", ["user_id"])
    op.create_index("ix_weekly_reports_week_start", "weekly_reports", ["week_start"])


def downgrade():
    op.drop_index("ix_weekly_reports_week_start", table_name="weekly_reports")
    op.drop_index("ix_weekly_reports_user_id", table_name="weekly_reports")
    op.drop_table("weekly_reports")
    op.drop_index("ix_attendances_user_id", table_name="attendances")
    op.drop_index("ix_attendances_attendance_date", table_name="attendances")
    op.drop_table("attendances")
    op.drop_index("ix_daily_logs_user_id", table_name="daily_logs")
    op.drop_index("ix_daily_logs_log_date", table_name="daily_logs")
    op.drop_table("daily_logs")
    op.drop_table("student_profiles")
