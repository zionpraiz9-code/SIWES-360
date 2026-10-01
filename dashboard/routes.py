from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user

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
    dashboard_endpoint = ROLE_DASHBOARDS.get(current_user.role)
    if dashboard_endpoint is None:
        flash("Your account role is not recognized.", "error")
        return redirect(url_for("auth.login"))
    return redirect(url_for(dashboard_endpoint))


@dashboard_bp.route("/student/dashboard")
@role_required("student")
def student_dashboard():
    return render_template("dashboard/student.html", user=current_user)


@dashboard_bp.route("/industry/dashboard")
@role_required("industry_supervisor")
def industry_dashboard():
    return render_template("dashboard/industry.html", user=current_user)


@dashboard_bp.route("/university/dashboard")
@role_required("university_supervisor")
def university_dashboard():
    return render_template("dashboard/university.html", user=current_user)


@dashboard_bp.route("/admin/dashboard")
@role_required("admin")
def admin_dashboard():
    return render_template("dashboard/admin.html", user=current_user)


@dashboard_bp.route("/student/reports/<int:report_id>/submit", methods=["POST"])
@role_required("student")
def report_submit(report_id):
    report = WeeklyReport.query.filter_by(id=report_id, student_id=_student_id()).first_or_404()
    if report.status == "Draft":
        report.status = "Submitted"
        db.session.commit()
        flash("Weekly report submitted.", "success")
    return redirect(url_for("dashboard.report_detail", report_id=report.id))


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
