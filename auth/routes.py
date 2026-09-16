from flask import flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError

from auth import auth_bp
from extensions import db
from models import VALID_ROLES, User


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role = request.form.get("role", "")

        if not all((name, email, password, confirm_password, role)):
            flash("All fields are required.", "error")
            return render_template("auth/register.html", roles=VALID_ROLES)
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return render_template("auth/register.html", roles=VALID_ROLES)
        if role not in VALID_ROLES:
            flash("Please select a valid role.", "error")
            return render_template("auth/register.html", roles=VALID_ROLES)
        if User.query.filter_by(email=email).first() is not None:
            flash("An account with that email is already registered.", "error")
            return render_template("auth/register.html", roles=VALID_ROLES)

        user = User(name=name, email=email, role=role)
        user.set_password(password)
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("An account with that email is already registered.", "error")
            return render_template("auth/register.html", roles=VALID_ROLES)

        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", roles=VALID_ROLES)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if user is None or not user.check_password(password):
            flash("Invalid email or password", "error")
            return render_template("auth/login.html")

        # Session data is the identity used by decorators until the next request.
        session.clear()
        session["user_id"] = user.id
        session["name"] = user.name
        session["role"] = user.role
        return redirect(url_for("dashboard.dashboard_router"))

    return render_template("auth/login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("auth.login"))
