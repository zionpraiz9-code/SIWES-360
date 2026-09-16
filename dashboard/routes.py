from flask import redirect, render_template, session, url_for

from dashboard import dashboard_bp
from decorators import login_required, role_required


ROLE_DASHBOARDS = {
    "student": "dashboard.student_dashboard",
    "industry_supervisor": "dashboard.industry_dashboard",
    "university_supervisor": "dashboard.university_dashboard",
    "admin": "dashboard.admin_dashboard",
}


@dashboard_bp.route("/dashboard")
@login_required
def dashboard_router():
    dashboard_endpoint = ROLE_DASHBOARDS.get(session.get("role"))
    if dashboard_endpoint is None:
        session.clear()
        return redirect(url_for("auth.login"))
    return redirect(url_for(dashboard_endpoint))


@dashboard_bp.route("/student/dashboard")
@role_required("student")
def student_dashboard():
    return render_template("dashboard/student.html")


@dashboard_bp.route("/industry/dashboard")
@role_required("industry_supervisor")
def industry_dashboard():
    return render_template("dashboard/industry.html")


@dashboard_bp.route("/university/dashboard")
@role_required("university_supervisor")
def university_dashboard():
    return render_template("dashboard/university.html")


@dashboard_bp.route("/admin/dashboard")
@role_required("admin")
def admin_dashboard():
    return render_template("dashboard/admin.html")
