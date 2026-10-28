from datetime import datetime, timezone

from flask_login import UserMixin
from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import validates
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"
    ROLES = (
        "student",
        "industry_supervisor",
        "university_supervisor",
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

    __table_args__ = (
        CheckConstraint(
            "role IN ('student', 'industry_supervisor', "
            "'university_supervisor', 'admin')",
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
