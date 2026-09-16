from functools import wraps

from flask import flash, redirect, session, url_for


def login_required(view):
    """Require a signed-in user before allowing the view to run."""
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "error")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped_view


def role_required(*roles):
    """Allow a view to declare one or more roles that may access it."""
    def decorator(view):
        @wraps(view)
        def wrapped_view(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "error")
                return redirect(url_for("auth.login"))

            if session.get("role") not in roles:
                flash("You are not authorized to view that dashboard.", "error")
                return redirect(url_for("dashboard.dashboard_router"))

            return view(*args, **kwargs)

        return wrapped_view

    return decorator
