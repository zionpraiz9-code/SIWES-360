from flask import Flask

from auth import auth_bp
from config import Config
from dashboard import dashboard_bp
from extensions import db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)

    with app.app_context():
        # Week 5 uses simple table creation; migrations can be introduced later.
        db.create_all()

    return app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True)
