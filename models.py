from datetime import date, datetime

from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


VALID_ROLES = (
    "student",
    "industry_supervisor",
    "university_supervisor",
    "admin",
)


class User(db.Model):
    __table_args__ = (
        db.CheckConstraint(
            "role IN ('student', 'industry_supervisor', 'university_supervisor', 'admin')",
            name="ck_user_role_valid",
        ),
    )

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    # One email identifies one account, so duplicate registrations are rejected.
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    skills = db.relationship("Skill", secondary="student_skills", backref="students")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class StudentProfile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), unique=True, nullable=False)
    organization = db.Column(db.String(160), nullable=True)
    siwes_start_date = db.Column(db.Date, nullable=True)
    siwes_end_date = db.Column(db.Date, nullable=True)

    user = db.relationship(
        "User",
        backref=db.backref("student_profile", uselist=False, cascade="all, delete-orphan"),
    )


class Attendance(db.Model):
    __table_args__ = (
        db.UniqueConstraint("student_id", "date", name="uq_attendance_student_date"),
    )

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False, default=date.today)
    status = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    student = db.relationship("User", backref=db.backref("attendance_records", lazy=True))


class Activity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    date = db.Column(db.Date, nullable=False)
    title = db.Column(db.String(160), nullable=False)
    description = db.Column(db.Text, nullable=False)
    skills = db.Column(db.String(255), nullable=True)
    tools = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    student = db.relationship("User", backref=db.backref("activities", lazy=True))


student_skills = db.Table(
    "student_skills",
    db.Column("student_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("skill_id", db.Integer, db.ForeignKey("skill.id"), primary_key=True),
)


class Skill(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class WeeklyReport(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    week_number = db.Column(db.Integer, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    summary = db.Column(db.Text, nullable=False)
    challenges = db.Column(db.Text, nullable=True)
    skills_acquired = db.Column(db.Text, nullable=True)
    supervisor_notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), nullable=False, default="Draft")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    student = db.relationship("User", backref=db.backref("weekly_reports", lazy=True))
