from urllib.parse import urlsplit

from flask import flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user
from sqlalchemy.exc import IntegrityError

from auth import auth_bp
from extensions import db
from models import SELF_REGISTERABLE_ROLES, User


def _safe_next_url():
    next_url = request.args.get("next", "")
    if not next_url:
        return ""
    if next_url.startswith("//"):
        return ""
    parsed = urlsplit(next_url)
    if parsed.scheme or parsed.netloc:
        return ""
    return next_url if next_url.startswith("/") else ""


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    roles = SELF_REGISTERABLE_ROLES

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role = request.form.get("role", "")

        if not all((name, email, password, confirm_password, role)):
            flash("All fields are required.", "error")
            return render_template("auth/register.html", roles=roles)
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("auth/register.html", roles=roles)
        if role not in roles:
            flash("Please select a valid role.", "error")
            return render_template("auth/register.html", roles=roles)
        if User.query.filter_by(email=email).first() is not None:
            flash("An account with that email is already registered.", "error")
            return render_template("auth/register.html", roles=roles)

        user = User(name=name, email=email, role=role, is_active=True)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("An account with that email is already registered.", "error")
            return render_template("auth/register.html", roles=roles)

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", roles=roles)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user is None or not user.check_password(password):
            flash("Invalid email or password", "error")
            return render_template("auth/login.html")

        if not user.is_active:
            flash("This account is inactive. Please contact an administrator.", "error")
            return render_template("auth/login.html")

        login_user(user)
        next_url = _safe_next_url()
        if next_url:
            return redirect(next_url)
        return redirect(url_for("dashboard.dashboard_router"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
