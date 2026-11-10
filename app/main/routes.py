from datetime import date, datetime, timedelta, timezone
from functools import wraps
from math import isfinite

from email_validator import EmailNotValidError, validate_email
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_mail import Message
from flask_login import current_user, login_required
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app import mail
from app.main.forms import (
    AdminCreateUserForm,
    DailyLogForm,
    PlacementForm,
    WeeklyReportForm,
)
from app.models import Attendance, DailyLog, StudentProfile, User, WeeklyReport
from extensions import db

main_bp = Blueprint("main", __name__)

ROLE_TITLES = {
    "student": "Student",
    "supervisor": "Industrial-Based Supervisor",
    "industry_supervisor": "Industry Supervisor",
    "university_supervisor": "University Supervisor",
    "school_supervisor": "School Supervisor",
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

    if profile and profile.start_date:
        expected_weekdays = _weekdays_between(profile.start_date, today)
        if expected_weekdays:
            present_dates = db.session.query(Attendance.attendance_date).filter(
                Attendance.user_id == current_user.id,
                Attendance.status == "present",
                Attendance.attendance_date >= profile.start_date,
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
        DailyLog.status == "Pending",
    ).count()
    pending_reports = WeeklyReport.query.filter(
        WeeklyReport.user_id == current_user.id,
        WeeklyReport.status == "Pending",
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
            profile.start_date if profile else None
        ),
        today=today,
    )


@main_bp.route("/student/full-report")
@login_required
def student_full_report():
    if current_user.role != "student":
        abort(403)

    profile = StudentProfile.query.filter_by(user_id=current_user.id).first()
    logs = DailyLog.query.filter_by(user_id=current_user.id).order_by(
        DailyLog.log_date.asc(),
        DailyLog.id.asc(),
    ).all()
    return render_template(
        "student/full_report.html",
        profile=profile,
        logs=logs,
        generated_on=date.today(),
    )


@main_bp.route("/student/logbook", methods=["GET", "POST"])
@roles_required("student")
def student_logbook():
    form = DailyLogForm()
    if form.validate_on_submit():
        profile = current_user.student_profile
        if profile is None:
            profile = StudentProfile(user_id=current_user.id)
            current_user.student_profile = profile
            db.session.add(profile)

        db.session.add(
            DailyLog(
                user_id=profile.user_id,
                log_date=form.log_date.data,
                title=form.title.data.strip(),
                activities=form.activities.data.strip(),
                tools_used=(form.tools_used.data or "").strip(),
                skills_learned=(form.skills_learned.data or "").strip(),
                challenges_encountered=(
                    form.challenges_encountered.data or ""
                ).strip(),
            )
        )
        db.session.commit()
        flash("Your daily log entry has been submitted.", "success")
        return redirect(url_for("main.student_logbook"))

    logs = DailyLog.query.filter_by(user_id=current_user.id).order_by(
        DailyLog.log_date.desc(),
        DailyLog.id.desc(),
    ).all()
    return (
        render_template(
            "main/student_logbook.html",
            form=form,
            logs=logs,
            today=date.today(),
        ),
        400 if request.method == "POST" else 200,
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
            report.status = "Pending"
            report.supervisor_comment = None
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


@main_bp.route("/student/weekly-reports", methods=["GET", "POST"])
@roles_required("student")
def student_weekly_reports():
    today = date.today()
    current_iso_date = today.isocalendar()
    current_week = current_iso_date.week
    form = WeeklyReportForm()
    profile = current_user.student_profile
    if profile is None:
        profile = StudentProfile(user_id=current_user.id)
        current_user.student_profile = profile
        db.session.add(profile)
    if profile.id is None:
        db.session.commit()

    if form.validate_on_submit():
        week_start = date.fromisocalendar(
            current_iso_date.year,
            form.week_number.data,
            1,
        )
        report = WeeklyReport.query.filter_by(
            user_id=profile.user_id,
            week_start=week_start,
        ).first()
        if report is None:
            report = WeeklyReport(
                user_id=profile.user_id,
                week_start=week_start,
            )
            db.session.add(report)

        report.summary = form.summary.data.strip()
        report.challenges_encountered = form.challenges_encountered.data.strip()
        report.plans_for_next_week = form.plans_for_next_week.data.strip()
        report.status = "Pending"
        report.supervisor_comment = None
        report.supervisor_feedback = None
        report.submitted_at = datetime.now(timezone.utc)
        db.session.commit()
        flash("Your weekly report has been submitted.", "success")
        return redirect(url_for("main.student_weekly_reports"))

    reports = WeeklyReport.query.filter_by(
        user_id=profile.user_id,
    ).order_by(
        WeeklyReport.week_start.desc(),
        WeeklyReport.id.desc(),
    ).all()
    return (
        render_template(
            "main/weekly_reports.html",
            form=form,
            reports=reports,
            current_week=current_week,
            current_year=current_iso_date.year,
        ),
        400 if request.method == "POST" else 200,
    )


@main_bp.route("/student/placement", methods=["GET", "POST"])
@roles_required("student")
def student_placement():
    profile = current_user.student_profile or StudentProfile()
    form = PlacementForm(obj=profile)
    if form.validate_on_submit():
        form.populate_obj(profile)
        if current_user.student_profile is None:
            current_user.student_profile = profile
        db.session.add(profile)
        db.session.commit()
        flash("Your industrial placement details have been saved.", "success")
        return redirect(url_for("main.student_placement"))

    return (
        render_template(
            "main/placement.html",
            form=form,
        ),
        400 if request.method == "POST" else 200,
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
    profile.start_date = start_date
    db.session.commit()
    flash("Your placement start date has been saved.", "success")
    return redirect(url_for("main.student_dashboard"))


@main_bp.route("/industry-supervisor/dashboard")
@roles_required("industry_supervisor")
def industry_supervisor_dashboard():
    return _render_supervisor_dashboard()


@main_bp.route("/supervisor/dashboard")
@login_required
def supervisor_dashboard():
    if current_user.role != "supervisor":
        flash(
            "You are not authorized to access the supervisor dashboard.",
            "warning",
        )
        return redirect(url_for("main.home"))
    return _render_supervisor_dashboard()


def _render_supervisor_dashboard():
    assigned_students = StudentProfile.query.filter(
        func.lower(StudentProfile.supervisor_email) == current_user.email.lower()
    ).order_by(StudentProfile.company_name, StudentProfile.user_id).all()
    student_progress = {
        profile.user_id: {
            "total_logs": 0,
            "pending_logs": 0,
            "approved_logs": 0,
            "rejected_logs": 0,
            "percentage": 0.0,
        }
        for profile in assigned_students
    }

    if student_progress:
        log_counts = (
            db.session.query(
                DailyLog.user_id,
                DailyLog.status,
                func.count(DailyLog.id),
            )
            .filter(DailyLog.user_id.in_(student_progress))
            .group_by(DailyLog.user_id, DailyLog.status)
            .all()
        )
        for user_id, status, count in log_counts:
            progress = student_progress[user_id]
            progress["total_logs"] += count
            if status == "Pending":
                progress["pending_logs"] += count
            elif status == "Approved":
                progress["approved_logs"] += count
            elif status == "Rejected":
                progress["rejected_logs"] += count

    total_logs = sum(
        progress["total_logs"] for progress in student_progress.values()
    )
    pending_logs = sum(
        progress["pending_logs"] for progress in student_progress.values()
    )
    approved_logs = sum(
        progress["approved_logs"] for progress in student_progress.values()
    )
    rejected_logs = sum(
        progress["rejected_logs"] for progress in student_progress.values()
    )
    for progress in student_progress.values():
        if progress["total_logs"]:
            progress["percentage"] = round(
                progress["approved_logs"] * 100 / progress["total_logs"],
                1,
            )

    return render_template(
        "main/supervisor_dashboard.html",
        assigned_students=assigned_students,
        student_progress=student_progress,
        total_logs=total_logs,
        pending_logs=pending_logs,
        approved_logs=approved_logs,
        rejected_logs=rejected_logs,
        approval_rate=(
            round(approved_logs * 100 / total_logs, 1) if total_logs else 0.0
        ),
        dashboard_endpoint=(
            "main.supervisor_dashboard"
            if current_user.role == "supervisor"
            else "main.industry_supervisor_dashboard"
        ),
    )


@main_bp.route("/supervisor/students/<int:student_id>/logs")
@login_required
def view_student_logs(student_id):
    if current_user.role not in {"supervisor", "industry_supervisor"}:
        flash("You are not authorized to review student logs.", "warning")
        return redirect(url_for("main.home"))

    profile = StudentProfile.query.filter(
        StudentProfile.user_id == student_id,
        func.lower(StudentProfile.supervisor_email) == current_user.email.lower(),
    ).first_or_404()
    logs = DailyLog.query.filter_by(user_id=profile.user_id).order_by(
        DailyLog.log_date.desc(),
        DailyLog.id.desc(),
    ).all()
    weekly_reports = WeeklyReport.query.filter_by(
        user_id=profile.user_id,
    ).order_by(
        WeeklyReport.week_start.desc(),
        WeeklyReport.id.desc(),
    ).all()
    return render_template(
        "main/supervisor_student_logs.html",
        profile=profile,
        logs=logs,
        weekly_reports=weekly_reports,
        dashboard_endpoint=(
            "main.supervisor_dashboard"
            if current_user.role == "supervisor"
            else "main.industry_supervisor_dashboard"
        ),
    )


@main_bp.route(
    "/supervisor/students/<int:student_id>/logs/<int:log_id>/review",
    methods=["POST"],
)
@login_required
def review_daily_log(log_id, student_id):
    if current_user.role != "supervisor":
        flash("You are not authorized to review daily logs.", "warning")
        return redirect(url_for("main.home"))

    profile = StudentProfile.query.filter(
        StudentProfile.user_id == student_id,
        func.lower(StudentProfile.supervisor_email) == current_user.email.lower(),
    ).first_or_404()
    log = DailyLog.query.filter_by(
        id=log_id,
        user_id=profile.user_id,
    ).first_or_404()

    status = request.form.get("status", "").strip()
    comment = request.form.get("supervisor_comment", "").strip()
    if status not in {"Approved", "Rejected"}:
        abort(400, description="Choose Approved or Rejected to review this log.")
    if len(comment) > 5000:
        abort(400, description="Supervisor comments must be 5,000 characters or fewer.")

    log.status = status
    log.supervisor_comment = comment or None
    log.supervisor_feedback = comment or None
    db.session.commit()
    if status == "Approved":
        flash("Daily log approved.", "success")
    else:
        flash("Daily log rejected and revision requested.", "info")
    return redirect(
        url_for("main.view_student_logs", student_id=profile.user_id)
    )


@main_bp.route(
    "/supervisor/students/<int:student_id>/weekly-reports/<int:report_id>/review",
    methods=["POST"],
)
@login_required
def review_weekly_report(report_id, student_id):
    if current_user.role != "supervisor":
        flash("You are not authorized to review weekly reports.", "warning")
        return redirect(url_for("main.home"))

    profile = StudentProfile.query.filter(
        StudentProfile.user_id == student_id,
        func.lower(StudentProfile.supervisor_email) == current_user.email.lower(),
    ).first_or_404()
    report = WeeklyReport.query.filter_by(
        id=report_id,
        user_id=profile.user_id,
    ).first_or_404()

    status = request.form.get("status", "").strip()
    comment = request.form.get("supervisor_comment", "").strip()
    if status not in {"Approved", "Rejected"}:
        abort(400, description="Choose Approved or Rejected to review this report.")
    if len(comment) > 5000:
        abort(
            400,
            description="Supervisor comments must be 5,000 characters or fewer.",
        )

    report.status = status
    report.supervisor_comment = comment or None
    report.supervisor_feedback = comment or None
    db.session.commit()
    if status == "Approved":
        flash("Weekly report approved.", "success")
    else:
        flash("Weekly report rejected and revision requested.", "info")
    return redirect(
        url_for("main.view_student_logs", student_id=profile.user_id)
    )


@main_bp.route("/university-supervisor/dashboard")
@roles_required("university_supervisor")
def university_supervisor_dashboard():
    return render_template(
        "main/university_supervisor_dashboard.html",
        dashboard_title=ROLE_TITLES["university_supervisor"],
    )


@main_bp.route("/school-supervisor/dashboard")
@login_required
def school_supervisor_dashboard():
    if current_user.role != "school_supervisor":
        abort(403)

    assigned_students = StudentProfile.query.filter(
        func.lower(StudentProfile.school_supervisor_email)
        == current_user.email.lower()
    ).order_by(StudentProfile.department, StudentProfile.user_id).all()
    return render_template(
        "main/school_supervisor_dashboard.html",
        assigned_students=assigned_students,
    )


@main_bp.route(
    "/school-supervisor/students/<int:student_id>/inspect",
    methods=["GET", "POST"],
)
@login_required
def school_supervisor_inspect(student_id):
    if current_user.role != "school_supervisor":
        abort(403)

    profile = StudentProfile.query.filter(
        StudentProfile.user_id == student_id,
        func.lower(StudentProfile.school_supervisor_email)
        == current_user.email.lower(),
    ).first_or_404()
    logs = DailyLog.query.filter_by(user_id=profile.user_id).order_by(
        DailyLog.log_date.desc(),
        DailyLog.id.desc(),
    ).all()
    weekly_reports = WeeklyReport.query.filter_by(
        user_id=profile.user_id,
    ).order_by(
        WeeklyReport.week_start.desc(),
        WeeklyReport.id.desc(),
    ).all()

    score_value = str(profile.academic_score)
    comment_value = profile.school_supervisor_comment or ""
    inspection_error = None
    if request.method == "POST":
        score_value = request.form.get("academic_score", "").strip()
        comment_value = request.form.get("school_supervisor_comment", "").strip()
        try:
            score = float(score_value)
        except ValueError:
            score = None

        if score is None or not isfinite(score) or score < 0:
            inspection_error = "Enter a valid academic score of zero or greater."
        elif len(comment_value) > 5000:
            inspection_error = "Academic comments must be 5,000 characters or fewer."
        else:
            profile.academic_score = score
            profile.school_supervisor_comment = comment_value or None
            db.session.commit()

            notification_failed = False
            try:
                student = db.session.get(User, profile.user_id)
                if student and student.email:
                    message = Message(
                        subject="Academic assessment updated | SIWES360",
                        recipients=[student.email],
                        body=(
                            f"Hello {student.full_name},\n\n"
                            "Your university school supervisor has updated your "
                            "academic assessment.\n\n"
                            f"New score: {score:g}\n"
                            "Comments: "
                            f"{comment_value or 'No comments provided.'}\n"
                        ),
                    )
                    mail.send(message)
                else:
                    notification_failed = True
                    current_app.logger.warning(
                        "Could not notify student user_id=%s: no email address.",
                        profile.user_id,
                    )
            except Exception:
                notification_failed = True
                current_app.logger.exception(
                    "Failed to send academic assessment notification "
                    "for student user_id=%s.",
                    profile.user_id,
                )

            if notification_failed:
                flash(
                    "Academic assessment saved, but the student notification "
                    "email could not be sent.",
                    "warning",
                )
            flash("Academic assessment saved.", "success")
            return redirect(
                url_for(
                    "main.school_supervisor_inspect",
                    student_id=profile.user_id,
                )
            )

    return render_template(
        "main/school_supervisor_inspect.html",
        profile=profile,
        logs=logs,
        weekly_reports=weekly_reports,
        score_value=score_value,
        comment_value=comment_value,
        inspection_error=inspection_error,
    ), 400 if inspection_error else 200


def _render_admin_dashboard(form=None):
    users = User.query.order_by(User.full_name, User.id).all()
    student_profiles = (
        StudentProfile.query.join(User)
        .filter(User.role == "student")
        .order_by(StudentProfile.company_name, StudentProfile.user_id)
        .all()
    )
    supervisor_roles = {
        "supervisor",
        "industry_supervisor",
        "university_supervisor",
        "school_supervisor",
    }
    return render_template(
        "main/admin_dashboard.html",
        form=form if form is not None else AdminCreateUserForm(),
        users=users,
        student_profiles=student_profiles,
        total_users=len(users),
        total_students=sum(user.role == "student" for user in users),
        total_supervisors=sum(user.role in supervisor_roles for user in users),
        assigned_students=sum(
            bool(profile.supervisor_email or profile.school_supervisor_email)
            for profile in student_profiles
        ),
    )


@main_bp.route("/admin/dashboard")
@roles_required("admin")
def admin_dashboard():
    return _render_admin_dashboard()


@main_bp.route("/admin/create-user", methods=["POST"])
@login_required
def admin_create_user():
    if current_user.role != "admin":
        abort(403)

    form = AdminCreateUserForm()
    if not form.validate_on_submit():
        return _render_admin_dashboard(form), 400

    email = form.email.data.strip().lower()
    if User.query.filter(func.lower(User.email) == email).first():
        form.email.errors.append("An account with this email already exists.")
        return _render_admin_dashboard(form), 409

    new_user = User(
        full_name=form.username.data.strip(),
        email=email,
        role=form.role.data,
    )
    new_user.set_password(form.password.data)
    db.session.add(new_user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if User.query.filter(func.lower(User.email) == email).first():
            form.email.errors.append("An account with this email already exists.")
            return _render_admin_dashboard(form), 409
        raise

    flash(f"Account created for {new_user.full_name}.", "success")
    return redirect(url_for("main.admin_dashboard"))


@main_bp.route("/admin/update-role/<int:user_id>", methods=["POST"])
@roles_required("admin")
def update_user_role(user_id):
    allowed_roles = {"student", "supervisor", "school_supervisor", "admin"}
    user = db.session.get(User, user_id)
    if user is None:
        abort(404)
    role = request.form.get("role", "").strip().lower()
    if role not in allowed_roles:
        flash("Choose a valid user role.", "danger")
        return redirect(url_for("main.admin_dashboard"))

    user.role = role
    db.session.commit()
    flash(f"{user.full_name}'s role was updated to {role.replace('_', ' ')}.", "success")
    return redirect(url_for("main.admin_dashboard"))


@main_bp.route(
    "/admin/allocate-supervisor/<int:student_id>",
    methods=["POST"],
)
@roles_required("admin")
def allocate_supervisor(student_id):
    profile = StudentProfile.query.filter_by(user_id=student_id).first_or_404()
    supervisor_email = request.form.get("supervisor_email", "").strip()
    school_supervisor_email = request.form.get(
        "school_supervisor_email",
        "",
    ).strip()

    email_fields = (
        ("Industrial supervisor", supervisor_email, 255),
        ("School supervisor", school_supervisor_email, 120),
    )
    normalized_emails = []
    for label, email, max_length in email_fields:
        if not email:
            normalized_emails.append(None)
            continue
        if len(email) > max_length:
            flash(f"{label} email must be {max_length} characters or fewer.", "danger")
            return redirect(url_for("main.admin_dashboard"))
        try:
            normalized_email = validate_email(
                email,
                check_deliverability=False,
            ).normalized.lower()
        except EmailNotValidError:
            flash(f"Enter a valid {label.lower()} email address.", "danger")
            return redirect(url_for("main.admin_dashboard"))
        normalized_emails.append(normalized_email)

    profile.supervisor_email, profile.school_supervisor_email = normalized_emails
    db.session.commit()
    flash("Supervisor assignments updated.", "success")
    return redirect(url_for("main.admin_dashboard"))
