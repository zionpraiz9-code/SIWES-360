from urllib.parse import urlsplit

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from app.auth.forms import ChangePasswordForm, LoginForm, RegistrationForm
from app.models import User
from extensions import db


auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

ROLE_DASHBOARDS = {
    "student": "main.student_dashboard",
    "industry_supervisor": "main.industry_supervisor_dashboard",
    "university_supervisor": "main.university_supervisor_dashboard",
    "admin": "main.admin_dashboard",
}


def _safe_next_url(target):
    if not target or any(ch in target for ch in ("\\", "\r", "\n")):
        return False

    parsed = urlsplit(target)
    if parsed.scheme or parsed.netloc:
        return False

    return target.startswith("/") and not target.startswith("//") and not target.startswith("/\\")


def _dashboard_redirect(user):
    return redirect(url_for(ROLE_DASHBOARDS[user.role]))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return _dashboard_redirect(current_user)

    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            full_name=form.full_name.data.strip(),
            email=form.email.data,
            role="student",
        )
        user.set_password(form.password.data)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("An account with this email already exists.", "danger")
            return render_template("auth/register.html", form=form), 409

        flash("Your student account was created. You can now log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return _dashboard_redirect(current_user)

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        user = User.query.filter(func.lower(User.email) == email).first()
        if user and user.is_active and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            flash(f"Welcome back, {user.full_name}.", "success")
            next_url = request.args.get("next")
            if _safe_next_url(next_url):
                return redirect(next_url)
            return _dashboard_redirect(user)

        flash("Email or password is incorrect.", "danger")

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    if current_user.is_authenticated:
        logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not current_user.check_password(form.current_password.data):
            form.current_password.errors.append("Current password is incorrect.")
        else:
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Your password has been changed.", "success")
            return _dashboard_redirect(current_user)

    return render_template("auth/change_password.html", form=form)
