from functools import wraps

from flask import Blueprint, abort, redirect, render_template, url_for
from flask_login import current_user, login_required


main_bp = Blueprint("main", __name__)

ROLE_TITLES = {
    "student": "Student",
    "industry_supervisor": "Industry Supervisor",
    "university_supervisor": "University Supervisor",
    "admin": "Administrator",
}


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped_view(*args, **kwargs):
            if current_user.role not in roles:
                abort(403)
            return view(*args, **kwargs)

        return wrapped_view

    return decorator


@main_bp.route("/")
def home():
    if current_user.is_authenticated:
        return redirect(url_for(f"main.{current_user.role}_dashboard"))
    return render_template("main/home.html")


@main_bp.route("/student/dashboard")
@roles_required("student")
def student_dashboard():
    return render_template(
        "main/student_dashboard.html",
        dashboard_title=ROLE_TITLES["student"],
    )


@main_bp.route("/industry-supervisor/dashboard")
@roles_required("industry_supervisor")
def industry_supervisor_dashboard():
    return render_template(
        "main/industry_supervisor_dashboard.html",
        dashboard_title=ROLE_TITLES["industry_supervisor"],
    )


@main_bp.route("/university-supervisor/dashboard")
@roles_required("university_supervisor")
def university_supervisor_dashboard():
    return render_template(
        "main/university_supervisor_dashboard.html",
        dashboard_title=ROLE_TITLES["university_supervisor"],
    )


@main_bp.route("/admin/dashboard")
@roles_required("admin")
def admin_dashboard():
    return render_template(
        "main/admin_dashboard.html",
        dashboard_title=ROLE_TITLES["admin"],
    )
