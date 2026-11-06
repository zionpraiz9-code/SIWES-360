from datetime import date, datetime, timezone

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, UniqueConstraint
from sqlalchemy.orm import synonym, validates
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"
    ROLES = (
        "student",
        "supervisor",
        "industry_supervisor",
        "university_supervisor",
        "school_supervisor",
        "admin",
    )

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), nullable=False, default="student")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    student_profile = db.relationship(
        "StudentProfile",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        CheckConstraint(
            "role IN ('student', 'supervisor', 'industry_supervisor', "
            "'university_supervisor', 'school_supervisor', 'admin')",
            name="ck_users_role",
        ),
    )

    @validates("full_name")
    def validate_full_name(self, _key, value):
        if not isinstance(value, str):
            raise ValueError("Full name is required.")
        normalized = value.strip()
        if len(normalized) < 2 or len(normalized) > 120:
            raise ValueError("Full name must be between 2 and 120 characters.")
        return normalized

    @validates("role")
    def validate_role(self, _key, value):
        if not isinstance(value, str):
            raise ValueError(f"Role must be one of: {', '.join(self.ROLES)}")
        normalized = value.strip().lower()
        if normalized not in self.ROLES:
            raise ValueError(f"Role must be one of: {', '.join(self.ROLES)}")
        return normalized

    @validates("email")
    def normalize_email(self, _key, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Email address is required.")
        return value.strip().lower()

    def set_password(self, password):
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters.")
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class StudentProfile(db.Model):
    __tablename__ = "student_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    matric_number = db.Column(db.String(64), nullable=True)
    department = db.Column(db.String(160), nullable=True)
    company_name = db.Column(db.String(160), nullable=True)
    company_address = db.Column(db.Text, nullable=True)
    supervisor_name = db.Column(db.String(120), nullable=True)
    supervisor_email = db.Column(db.String(255), nullable=True)
    supervisor_phone = db.Column(db.String(32), nullable=True)
    school_supervisor_email = db.Column(db.String(120), nullable=True)
    academic_score = db.Column(db.Float, nullable=False, default=0.0)
    school_supervisor_comment = db.Column(db.Text, nullable=True)
    start_date = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    placement_start_date = synonym("start_date")

    user = db.relationship("User", back_populates="student_profile")


class DailyLog(db.Model):
    __tablename__ = "daily_logs"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    log_date = db.Column(db.Date, nullable=False, index=True, default=date.today)
    title = db.Column(db.String(120), nullable=False)
    activities = db.Column(db.Text, nullable=False)
    tools_used = db.Column(db.Text, nullable=False, default="", server_default="")
    skills_learned = db.Column(db.Text, nullable=False, default="", server_default="")
    challenges_encountered = db.Column(
        db.Text,
        nullable=False,
        default="",
        server_default="",
    )
    status = db.Column(
        db.String(16),
        nullable=False,
        default="Pending",
        server_default="Pending",
    )
    supervisor_comment = db.Column(db.Text, nullable=True)
    supervisor_feedback = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('Pending', 'Approved', 'Rejected')",
            name="ck_daily_logs_status",
        ),
    )


class Attendance(db.Model):
    __tablename__ = "attendances"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    attendance_date = db.Column(db.Date, nullable=False, index=True)
    status = db.Column(db.String(16), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("user_id", "attendance_date", name="uq_attendance_user_date"),
        CheckConstraint(
            "status IN ('present', 'absent')",
            name="ck_attendances_status",
        ),
    )


class WeeklyReport(db.Model):
    __tablename__ = "weekly_reports"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    week_start = db.Column(db.Date, nullable=False, index=True)
    summary = db.Column(db.Text, nullable=False)
    challenges_encountered = db.Column(
        db.Text,
        nullable=False,
        default="",
        server_default="",
    )
    plans_for_next_week = db.Column(
        db.Text,
        nullable=False,
        default="",
        server_default="",
    )
    status = db.Column(
        db.String(16),
        nullable=False,
        default="Pending",
        server_default="Pending",
    )
    supervisor_comment = db.Column(db.Text, nullable=True)
    supervisor_feedback = db.Column(db.Text, nullable=True)
    submitted_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    __table_args__ = (
        UniqueConstraint("user_id", "week_start", name="uq_weekly_report_user_week"),
        CheckConstraint(
            "status IN ('Pending', 'Approved', 'Rejected')",
            name="ck_weekly_reports_status",
        ),
    )
