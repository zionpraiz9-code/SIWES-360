# SIWES360

SIWES360 is a Flask application for coordinating student industrial training
records. This repository currently contains the project foundation and an
initial role-aware authentication workflow; logbooks, placements, attendance,
reports, evaluations, notifications, and their supervisor workflows are not
implemented yet.

## Requirements

- Python 3.10 or newer
- PowerShell on Windows

## Set up on Windows

From the repository directory:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Replace `SECRET_KEY` in `.env` with a locally generated value. For example:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the printed value into `.env`. Keep `.env` private and out of version
control. `DATABASE_URL` may remain empty to use the local SQLite database at
`instance/siwes360.db`. For PostgreSQL, set it to a PostgreSQL SQLAlchemy URL.

Assessment notification emails use Flask-Mail. Configure `MAIL_SERVER`,
`MAIL_PORT`, `MAIL_USE_TLS` or `MAIL_USE_SSL`, `MAIL_USERNAME`, `MAIL_PASSWORD`,
and `MAIL_DEFAULT_SENDER` in `.env` for your SMTP provider. If email delivery
fails, the assessment is still saved and the failure is logged.

## Database migrations

Create the initial migration once, then apply it:

```powershell
flask --app run.py db init
flask --app run.py db migrate -m "Initial schema"
flask --app run.py db upgrade
```

After changing SQLAlchemy models, generate and apply a new migration:

```powershell
flask --app run.py db migrate -m "Describe the schema change"
flask --app run.py db upgrade
```

Review generated migration scripts before applying them. Do not use
`db.create_all()` to manage an evolving application schema.

If an existing local database is behind the models, apply pending migrations
to preserve its data:

```powershell
python -m flask --app run.py db upgrade
```

For a disposable local database only, the following app-context snippet drops
and recreates the mapped tables. It refuses to run unless the configured
database is the project's default SQLite file. This permanently deletes its
data:

```python
from pathlib import Path

from app import create_app
from extensions import db

app = create_app({"FLASK_CONFIG": "development"})
with app.app_context():
    expected_database = (Path(app.instance_path) / "siwes360.db").resolve()
    configured_database = Path(db.engine.url.database).resolve()
    if db.engine.dialect.name != "sqlite" or configured_database != expected_database:
        raise RuntimeError("Refusing to reset a non-default local SQLite database.")

    db.session.remove()
    db.drop_all()
    db.create_all()
```

After running the snippet, synchronize Alembic's version marker with the
recreated schema:

```powershell
python -m flask --app run.py db stamp head
```

## Run the application

```powershell
flask --app run.py run
```

Open `http://127.0.0.1:5000/`. The health endpoint is
`http://127.0.0.1:5000/health` and returns a small JSON status response.

The current bootstrap command can create a privileged account from a trusted
local terminal; do not expose administrative account creation publicly:

```powershell
flask --app run.py create-user
```

## Tests

```powershell
python -m pytest
```

The tests use an isolated in-memory SQLite database and do not use the local
development database.

## Initial architecture and data model

The Flask application factory in `app/__init__.py` configures extensions,
registers blueprints, and installs command-line operations. Shared extension
instances live in `extensions.py`; configuration profiles live in `config.py`.
The `User` table currently stores a unique email, a password hash, a supported
role, and account activity status. Public registration always creates a student
account; privileged roles are provisioned through the trusted CLI.

Initial entity relationship:

```text
User
 ├── id (primary key)
 ├── full_name
 ├── email (unique)
 ├── password_hash
 ├── role
 └── is_active
```

The placement, logbook, weekly report, attendance, skill, evaluation,
supervision visit, notification, and audit entities described in the project
specification remain future implementation work. They should be related to
users with explicit foreign keys and authorization checks when added.

## Security notes

- Set a strong, private `SECRET_KEY` before running outside a local development
  environment.
- Production configuration disables debug mode and requires secure session
  cookies over HTTPS.
- Passwords are stored using Werkzeug password hashing.
- Flask-WTF CSRF protection is enabled outside the isolated test setup.
- The application does not include a default administrator password.

## Current implementation status

Implemented: Flask application factory, development/testing/production
configuration, SQLAlchemy and migration integration, public landing page,
health endpoint, student registration, login/logout, password hashing,
authenticated password changes, role-specific placeholder dashboards, and an
initial authentication test suite.

Not yet implemented: placement assignment, logbook and report lifecycles,
attendance and skills management, supervisor reviews and visits, evaluations,
notifications, analytics, administrative workflows, and full defence/deployment
documentation. Dashboard pages are not evidence that these workflows exist.
