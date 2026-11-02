from datetime import date, datetime, timedelta, timezone
from functools import wraps

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required

from app.models import Attendance, DailyLog, StudentProfile, WeeklyReport
from extensions import db

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
    today = date.today()
    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    log_query = DailyLog.query.filter_by(user_id=current_user.id)
    attendance_percentage = None

    if profile and profile.placement_start_date:
        expected_weekdays = _weekdays_between(profile.placement_start_date, today)
        if expected_weekdays:
            present_dates = db.session.query(Attendance.attendance_date).filter(
                Attendance.user_id == current_user.id,
                Attendance.status == "present",
                Attendance.attendance_date >= profile.placement_start_date,
                Attendance.attendance_date <= today,
            )
            present_weekdays = sum(
                attendance_date.weekday() < 5
                for (attendance_date,) in present_dates
            )
            attendance_percentage = round(
                present_weekdays * 100 / expected_weekdays
            )
        else:
            attendance_percentage = 0

    week_start = today - timedelta(days=today.weekday())
    weekly_report = WeeklyReport.query.filter_by(
        user_id=current_user.id,
        week_start=week_start,
    ).first()
    pending_logs = DailyLog.query.filter(
        DailyLog.user_id == current_user.id,
        DailyLog.supervisor_feedback.is_(None),
    ).count()
    pending_reports = WeeklyReport.query.filter(
        WeeklyReport.user_id == current_user.id,
        WeeklyReport.status == "submitted",
        WeeklyReport.supervisor_feedback.is_(None),
    ).count()

    return render_template(
        "main/student_dashboard.html",
        dashboard_title=ROLE_TITLES["student"],
        attendance_percentage=attendance_percentage,
        daily_log_count=log_query.count(),
        weekly_report=weekly_report,
        pending_feedback_count=pending_logs + pending_reports,
        recent_logs=log_query.order_by(
            DailyLog.log_date.desc(),
            DailyLog.id.desc(),
        ).limit(5).all(),
        placement_start_date=(
            profile.placement_start_date if profile else None
        ),
        today=today,
    )


def _weekdays_between(start_date, end_date):
    if start_date > end_date:
        return 0
    total_days = (end_date - start_date).days + 1
    full_weeks, remaining_days = divmod(total_days, 7)
    return full_weeks * 5 + sum(
        (start_date.weekday() + offset) % 7 < 5
        for offset in range(remaining_days)
    )


def _render_student_action(action, title, description, status=200, error=None):
    return (
        render_template(
            "main/student_action_form.html",
            action=action,
            action_title=title,
            action_description=description,
            today=date.today(),
            form_values=request.form,
            error=error,
        ),
        status,
    )


def _parse_form_date(field_name):
    try:
        return date.fromisoformat(request.form.get(field_name, ""))
    except ValueError:
        return None


@main_bp.route("/student/logs/new", methods=["GET", "POST"])
@roles_required("student")
def new_daily_log():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        activities = request.form.get("activities", "").strip()
        log_date = _parse_form_date("log_date")
        if not title or len(title) > 120:
            return _render_student_action(
                "log",
                "New log entry",
                "Record the work and skills you developed today.",
                400,
                "Enter a log title of no more than 120 characters.",
            )
        if not activities or len(activities) > 5000:
            return _render_student_action(
                "log",
                "New log entry",
                "Record the work and skills you developed today.",
                400,
                "Enter activities using no more than 5,000 characters.",
            )
        if not log_date or log_date > date.today():
            return _render_student_action(
                "log",
                "New log entry",
                "Record the work and skills you developed today.",
                400,
                "Choose a valid date that is not in the future.",
            )

        db.session.add(
            DailyLog(
                user_id=current_user.id,
                log_date=log_date,
                title=title,
                activities=activities,
            )
        )
        db.session.commit()
        flash("Your daily log entry has been submitted.", "success")
        return redirect(url_for("main.student_dashboard"))

    return _render_student_action(
        "log",
        "New log entry",
        "Record the work and skills you developed today.",
    )


@main_bp.route("/student/attendance/mark", methods=["GET", "POST"])
@roles_required("student")
def mark_attendance():
    if request.method == "POST":
        attendance_date = _parse_form_date("attendance_date")
        status = request.form.get("status", "")
        if not attendance_date or attendance_date > date.today():
            return _render_student_action(
                "attendance",
                "Mark attendance",
                "Record your attendance for a training day.",
                400,
                "Choose a valid attendance date that is not in the future.",
            )
        if status not in {"present", "absent"}:
            return _render_student_action(
                "attendance",
                "Mark attendance",
                "Record your attendance for a training day.",
                400,
                "Choose either present or absent.",
            )

        attendance = Attendance.query.filter_by(
            user_id=current_user.id,
            attendance_date=attendance_date,
        ).first()
        if attendance:
            attendance.status = status
        else:
            db.session.add(
                Attendance(
                    user_id=current_user.id,
                    attendance_date=attendance_date,
                    status=status,
                )
            )
        db.session.commit()
        flash("Your attendance has been recorded.", "success")
        return redirect(url_for("main.student_dashboard"))

    return _render_student_action(
        "attendance",
        "Mark attendance",
        "Record your attendance for a training day.",
    )


@main_bp.route("/student/reports/weekly", methods=["GET", "POST"])
@roles_required("student")
def submit_weekly_report():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    if request.method == "POST":
        summary = request.form.get("summary", "").strip()
        if not summary or len(summary) > 10000:
            return _render_student_action(
                "report",
                "Submit weekly report",
                "Summarize your training progress for this week.",
                400,
                "Enter a summary using no more than 10,000 characters.",
            )

        report = WeeklyReport.query.filter_by(
            user_id=current_user.id,
            week_start=week_start,
        ).first()
        if report:
            report.summary = summary
            report.status = "submitted"
            report.supervisor_feedback = None
            report.submitted_at = datetime.now(timezone.utc)
        else:
            db.session.add(
                WeeklyReport(
                    user_id=current_user.id,
                    week_start=week_start,
                    summary=summary,
                )
            )
        db.session.commit()
        flash("Your weekly report has been submitted.", "success")
        return redirect(url_for("main.student_dashboard"))

    return _render_student_action(
        "report",
        "Submit weekly report",
        "Summarize your training progress for this week.",
    )


@main_bp.route("/student/profile/placement-start", methods=["POST"])
@roles_required("student")
def set_placement_start():
    start_date = _parse_form_date("placement_start_date")
    if not start_date or start_date > date.today():
        flash("Choose a valid placement start date that is not in the future.", "danger")
        return redirect(url_for("main.student_dashboard"))

    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    if profile is None:
        profile = StudentProfile(user_id=current_user.id)
        db.session.add(profile)
    profile.placement_start_date = start_date
    db.session.commit()
    flash("Your placement start date has been saved.", "success")
    return redirect(url_for("main.student_dashboard"))


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
