import click
from flask import Flask, render_template
from flask.cli import with_appcontext
from werkzeug.utils import import_string

from auth import auth_bp
from config import Config
from dashboard import dashboard_bp
from extensions import csrf, db, login_manager, migrate
from models import User


def create_app(config_class=Config):
    if isinstance(config_class, str):
        config_class = import_string(config_class)

    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to continue."
    login_manager.login_message_category = "error"

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)

    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template("errors/500.html"), 500

    @app.cli.command("create-admin")
    @click.option("--name", default="Admin User")
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    @with_appcontext
    def create_admin(name, email, password):
        if User.query.filter_by(email=email.lower().strip()).first():
            raise click.ClickException("An account with that email already exists.")

        admin = User(name=name.strip(), email=email.lower().strip(), role="admin", is_active=True)
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo(f"Admin created: {admin.email}")

    with app.app_context():
        db.create_all()

    return app


app = create_app(Config)


if __name__ == "__main__":
    app.run(debug=True)
