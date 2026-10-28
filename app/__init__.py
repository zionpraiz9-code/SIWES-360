import click
import os
from datetime import datetime
from email_validator import EmailNotValidError, validate_email
from flask import Flask, jsonify
from sqlalchemy import func
from werkzeug.security import generate_password_hash

from config import CONFIG_BY_NAME
from extensions import csrf, db, login_manager, migrate


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    config_name = (test_config or {}).get(
        "FLASK_CONFIG",
        os.environ.get("FLASK_CONFIG", "development"),
    )
    config_class = CONFIG_BY_NAME.get(config_name)
    if config_class is None:
        raise RuntimeError(
            f"Unknown FLASK_CONFIG '{config_name}'. "
            f"Choose one of: {', '.join(CONFIG_BY_NAME)}."
        )
    app.config.from_object(config_class)
    if test_config:
        app.config.update(test_config)

    if not app.config.get("SECRET_KEY"):
        raise RuntimeError(
            "SECRET_KEY is required. Set it in your environment or .env file."
        )

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access that page."
    login_manager.login_message_category = "info"

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        if not user_id.isdecimal():
            return None
        return db.session.get(User, int(user_id))

    from app.auth.routes import auth_bp
    from app.main.routes import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_current_year():
        return {"current_year": datetime.now().year}

    @app.cli.command("create-user")
    def create_user_command():
        """Create a user from the trusted local command line."""
        full_name = click.prompt("Full name").strip()
        if len(full_name) < 2 or len(full_name) > 120:
            raise click.ClickException("Full name must be between 2 and 120 characters.")

        email_input = click.prompt("Email").strip()
        try:
            email = validate_email(email_input, check_deliverability=False).normalized.lower()
        except EmailNotValidError as error:
            raise click.ClickException(f"Invalid email address: {error}") from error

        role = click.prompt(
            "Role",
            type=click.Choice(User.ROLES, case_sensitive=True),
        )
        if User.query.filter(func.lower(User.email) == email).first():
            raise click.ClickException("An account with that email already exists.")

        password = click.prompt("Password (minimum 8 characters)", hide_input=True)
        confirmation = click.prompt("Confirm password", hide_input=True)
        if len(password) < 8:
            raise click.ClickException("Password must be at least 8 characters.")
        if password != confirmation:
            raise click.ClickException("The passwords do not match.")

        user = User(full_name=full_name, email=email, role=role)
        user.password_hash = generate_password_hash(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Created {role} account for {email}.")

    @app.errorhandler(403)
    def forbidden(_error):
        return app.send_static_file("403.html"), 403

    @app.get("/health")
    def health():
        return jsonify(status="ok", application="SIWES360"), 200

    return app
