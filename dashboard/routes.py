from datetime import date, datetime

from flask import flash, redirect, render_template, request, session, url_for

from dashboard import dashboard_bp
from decorators import login_required, role_required
from extensions import db
from models import Activity, Attendance, Skill, StudentProfile, User, WeeklyReport, student_skills


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
    user = User.query.get_or_404(session["user_id"])
    profile = StudentProfile.query.filter_by(user_id=user.id).first()
    if profile is None:
        profile = StudentProfile(user_id=user.id)
        db.session.add(profile)
        db.session.commit()

    total_days = 0
    days_completed = 0
    if profile.siwes_start_date and profile.siwes_end_date:
        total_days = max((profile.siwes_end_date - profile.siwes_start_date).days + 1, 0)
        days_completed = min(max((date.today() - profile.siwes_start_date).days + 1, 0), total_days)
    days_remaining = max(total_days - days_completed, 0)
    progress = round((days_completed / total_days) * 100) if total_days else 0
    attendance_total = Attendance.query.filter_by(student_id=user.id).count()
    present_days = Attendance.query.filter_by(student_id=user.id, status="Present").count()

    dashboard_data = {
        "organization": profile.organization or "Not assigned",
        "start_date": profile.siwes_start_date,
        "end_date": profile.siwes_end_date,
        "progress": progress,
        "days_completed": days_completed,
        "days_remaining": days_remaining,
        "attendance": round((present_days / attendance_total) * 100) if attendance_total else 0,
        "activities": Activity.query.filter_by(student_id=user.id).count(),
        "reports": WeeklyReport.query.filter_by(student_id=user.id, status="Submitted").count(),
        "skills": db.session.query(student_skills).filter_by(student_id=user.id).count(),
    }
    return render_template("dashboard/student.html", user=user, profile=profile, dashboard_data=dashboard_data)


def _student_id():
    return session["user_id"]


def _parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


@dashboard_bp.route("/student/profile", methods=["GET", "POST"])
@role_required("student")
def student_profile():
    profile = StudentProfile.query.filter_by(user_id=_student_id()).first()
    if profile is None:
        profile = StudentProfile(user_id=_student_id())
        db.session.add(profile)
        db.session.commit()

    if request.method == "POST":
        profile.organization = request.form.get("organization", "").strip() or None
        try:
            start_date = request.form.get("siwes_start_date", "")
            end_date = request.form.get("siwes_end_date", "")
            profile.siwes_start_date = _parse_date(start_date) if start_date else None
            profile.siwes_end_date = _parse_date(end_date) if end_date else None
        except ValueError:
            flash("Please enter valid SIWES dates.", "error")
            return render_template("student/profile_form.html", profile=profile)
        if profile.siwes_start_date and profile.siwes_end_date and profile.siwes_end_date < profile.siwes_start_date:
            flash("The SIWES end date cannot be before the start date.", "error")
            return render_template("student/profile_form.html", profile=profile)
        db.session.commit()
        flash("Student profile updated.", "success")
        return redirect(url_for("dashboard.student_dashboard"))
    return render_template("student/profile_form.html", profile=profile)


@dashboard_bp.route("/student/attendance", methods=["GET", "POST"])
@role_required("student")
def attendance_page():
    if request.method == "POST":
        try:
            record_date = _parse_date(request.form.get("date", ""))
        except ValueError:
            flash("Please enter a valid attendance date.", "error")
            return redirect(url_for("dashboard.attendance_page"))
        status = request.form.get("status", "")
        if status not in ("Present", "Absent"):
            flash("Choose Present or Absent.", "error")
        elif Attendance.query.filter_by(student_id=_student_id(), date=record_date).first():
            flash("Attendance has already been recorded for that date.", "error")
        else:
            db.session.add(Attendance(student_id=_student_id(), date=record_date, status=status))
            db.session.commit()
            flash("Attendance recorded.", "success")
        return redirect(url_for("dashboard.attendance_page"))
    records = Attendance.query.filter_by(student_id=_student_id()).order_by(Attendance.date.desc()).all()
    return render_template("student/attendance.html", records=records, today=date.today())


@dashboard_bp.route("/student/activities")
@role_required("student")
def activities():
    records = Activity.query.filter_by(student_id=_student_id()).order_by(Activity.date.desc()).all()
    return render_template("student/activities.html", activities=records)


@dashboard_bp.route("/student/activities/new", methods=["GET", "POST"])
@role_required("student")
def activity_new():
    if request.method == "POST":
        try:
            activity_date = _parse_date(request.form.get("date", ""))
        except ValueError:
            flash("Please enter a valid activity date.", "error")
            return render_template("student/activity_form.html", activity=None)
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        if not title or not description:
            flash("Activity title and description are required.", "error")
            return render_template("student/activity_form.html", activity=None)
        db.session.add(Activity(
            student_id=_student_id(), date=activity_date, title=title,
            description=description, skills=request.form.get("skills", "").strip(),
            tools=request.form.get("tools", "").strip(),
        ))
        db.session.commit()
        flash("Activity added.", "success")
        return redirect(url_for("dashboard.activities"))
    return render_template("student/activity_form.html", activity=None)


@dashboard_bp.route("/student/activities/<int:activity_id>")
@role_required("student")
def activity_detail(activity_id):
    activity = Activity.query.filter_by(id=activity_id, student_id=_student_id()).first_or_404()
    return render_template("student/activity_detail.html", activity=activity)


@dashboard_bp.route("/student/activities/<int:activity_id>/edit", methods=["GET", "POST"])
@role_required("student")
def activity_edit(activity_id):
    activity = Activity.query.filter_by(id=activity_id, student_id=_student_id()).first_or_404()
    if request.method == "POST":
        try:
            activity.date = _parse_date(request.form.get("date", ""))
        except ValueError:
            flash("Please enter a valid activity date.", "error")
            return render_template("student/activity_form.html", activity=activity)
        activity.title = request.form.get("title", "").strip()
        activity.description = request.form.get("description", "").strip()
        activity.skills = request.form.get("skills", "").strip()
        activity.tools = request.form.get("tools", "").strip()
        if not activity.title or not activity.description:
            flash("Activity title and description are required.", "error")
            return render_template("student/activity_form.html", activity=activity)
        db.session.commit()
        flash("Activity updated.", "success")
        return redirect(url_for("dashboard.activity_detail", activity_id=activity.id))
    return render_template("student/activity_form.html", activity=activity)


@dashboard_bp.route("/student/activities/<int:activity_id>/delete", methods=["POST"])
@role_required("student")
def activity_delete(activity_id):
    activity = Activity.query.filter_by(id=activity_id, student_id=_student_id()).first_or_404()
    db.session.delete(activity)
    db.session.commit()
    flash("Activity deleted.", "success")
    return redirect(url_for("dashboard.activities"))


@dashboard_bp.route("/student/skills", methods=["GET", "POST"])
@role_required("student")
def skills():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Skill name is required.", "error")
        else:
            skill = Skill.query.filter_by(name=name).first()
            if skill is None:
                skill = Skill(name=name)
                db.session.add(skill)
                db.session.flush()
            student = User.query.get(_student_id())
            if skill not in student.skills:
                student.skills.append(skill)
                db.session.commit()
                flash("Skill added.", "success")
            else:
                flash("That skill is already in your list.", "error")
        return redirect(url_for("dashboard.skills"))
    student = User.query.get(_student_id())
    return render_template("student/skills.html", skills=student.skills)


@dashboard_bp.route("/student/skills/<int:skill_id>/delete", methods=["POST"])
@role_required("student")
def skill_delete(skill_id):
    student = User.query.get(_student_id())
    skill = next((item for item in student.skills if item.id == skill_id), None)
    if skill is None:
        return ("Not found", 404)
    student.skills.remove(skill)
    db.session.commit()
    flash("Skill removed.", "success")
    return redirect(url_for("dashboard.skills"))


@dashboard_bp.route("/student/reports")
@role_required("student")
def reports():
    records = WeeklyReport.query.filter_by(student_id=_student_id()).order_by(WeeklyReport.week_number.desc()).all()
    return render_template("student/reports.html", reports=records)


def _report_form():
    values = request.form
    try:
        week_number = int(values.get("week_number", ""))
        start_date = _parse_date(values.get("start_date", ""))
        end_date = _parse_date(values.get("end_date", ""))
    except ValueError:
        raise ValueError("Week, start date, and end date are required and must be valid.")
    if week_number < 1 or end_date < start_date:
        raise ValueError("Enter a valid week and make sure the end date is not before the start date.")
    data = {
        "week_number": week_number,
        "start_date": start_date,
        "end_date": end_date,
        "summary": values.get("summary", "").strip(),
        "challenges": values.get("challenges", "").strip(),
        "skills_acquired": values.get("skills_acquired", "").strip(),
        "supervisor_notes": values.get("supervisor_notes", "").strip(),
    }
    if not data["summary"]:
        raise ValueError("A report summary is required.")
    return data


@dashboard_bp.route("/student/reports/new", methods=["GET", "POST"])
@role_required("student")
def report_new():
    if request.method == "POST":
        try:
            data = _report_form()
        except ValueError as error:
            flash(str(error), "error")
            return render_template("student/report_form.html", report=None)
        db.session.add(WeeklyReport(student_id=_student_id(), **data))
        db.session.commit()
        flash("Weekly report saved as a draft.", "success")
        return redirect(url_for("dashboard.reports"))
    return render_template("student/report_form.html", report=None)


@dashboard_bp.route("/student/reports/<int:report_id>")
@role_required("student")
def report_detail(report_id):
    report = WeeklyReport.query.filter_by(id=report_id, student_id=_student_id()).first_or_404()
    return render_template("student/report_detail.html", report=report)


@dashboard_bp.route("/student/reports/<int:report_id>/edit", methods=["GET", "POST"])
@role_required("student")
def report_edit(report_id):
    report = WeeklyReport.query.filter_by(id=report_id, student_id=_student_id()).first_or_404()
    if report.status != "Draft":
        flash("Submitted reports cannot be edited.", "error")
        return redirect(url_for("dashboard.report_detail", report_id=report.id))
    if request.method == "POST":
        try:
            for key, value in _report_form().items():
                setattr(report, key, value)
        except ValueError as error:
            flash(str(error), "error")
            return render_template("student/report_form.html", report=report)
        db.session.commit()
        flash("Weekly report updated.", "success")
        return redirect(url_for("dashboard.report_detail", report_id=report.id))
    return render_template("student/report_form.html", report=report)


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
