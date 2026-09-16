from datetime import datetime

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

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
