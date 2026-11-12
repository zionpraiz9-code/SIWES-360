# SIWES360

SIWES360 is a Flask web application for managing student industrial training
placements, activity logs, attendance, weekly reports, and supervisor reviews.

**Live website:** [siwes360.pythonanywhere.com](https://siwes360.pythonanywhere.com/)

## Features

- Student registration, login/logout, and password changes.
- Role-specific dashboards for students, supervisors, university supervisors,
  school supervisors, industry supervisors, and administrators.
- Student placement details, daily logbooks, attendance, and weekly reports.
- Supervisor review of student daily logs and weekly reports.
- School supervisor review of student records and academic assessment, with
  optional email notification.
- Administrator account creation, role updates, and supervisor allocation.
- SQLAlchemy persistence with versioned Flask-Migrate/Alembic migrations.

## Requirements

- Python 3.10 or newer
- PowerShell on Windows (commands below use PowerShell syntax)

## Installation

Run these commands from the repository root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Set a unique `SECRET_KEY` in `.env`. Generate one locally with:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Keep `.env` private and never commit real credentials. The example file contains
all application environment variables and safe local-development defaults.

## Environment variables

`run.py` loads variables from `.env`. The same variables can be set directly in
the process environment.

| Variable | Default | Description |
| --- | --- | --- |
| `FLASK_CONFIG` | `development` | Configuration profile: `development`, `testing`, or `production`. |
| `SECRET_KEY` | `dev-secret-key` | Flask session and CSRF signing key. Set a strong, random value outside local development. |
| `DATABASE_URL` | Empty (uses `sqlite:///siwes360.db`) | SQLAlchemy database URL. The default database is stored at `instance/siwes360.db`. Leave empty to use SQLite. |
| `SESSION_COOKIE_SECURE` | `false` | Enables the `Secure` session-cookie flag when set to `1`, `true`, or `yes`. The production profile always enables it; use production behind HTTPS. |
| `MAIL_SERVER` | `localhost` | SMTP server hostname for assessment email notifications. |
| `MAIL_PORT` | `25` | SMTP server port. |
| `MAIL_USE_TLS` | `false` | Enables SMTP STARTTLS when set to `1`, `true`, or `yes`. |
| `MAIL_USE_SSL` | `false` | Enables SMTP SSL when set to `1`, `true`, or `yes`. Configure TLS or SSL according to your provider. |
| `MAIL_USERNAME` | Empty | SMTP account username, if required. |
| `MAIL_PASSWORD` | Empty | SMTP account password, if required. Store it only in a private environment or `.env` file. |
| `MAIL_DEFAULT_SENDER` | Empty | Sender address for outgoing assessment notifications. |

Email is optional. Configure the `MAIL_*` values for your SMTP provider to send
assessment notifications. An email failure is logged and shown as a warning;
the assessment itself remains saved.

## Database

The repository already includes migration history. After installation and
configuration, apply pending migrations (this also prepares a fresh database):

```powershell
flask --app run.py db upgrade
```

After changing SQLAlchemy models, create and review a migration, then apply it:

```powershell
flask --app run.py db migrate -m "Describe the schema change"
flask --app run.py db upgrade
```

Do not run `db init` on this repository or use `db.create_all()` to manage an
evolving schema. Back up important database data before applying migrations.

## Run

```powershell
flask --app run.py run
```

Open `http://127.0.0.1:5000/`. The health check at
`http://127.0.0.1:5000/health` returns a JSON status response.

Create a privileged account from a trusted terminal when needed:

```powershell
flask --app run.py create-user
```

The command prompts for a name, email, supported role, and password. Do not
expose privileged account provisioning as a public service.

## Tests

Run the test suite with:

```powershell
python -m pytest
```

Tests use an isolated in-memory SQLite database and do not use the local
development database.

## Project layout

```text
app/
  auth/          Registration, login, and password-management routes/forms
  main/          SIWES workflows, dashboards, and forms
  static/        CSS, JavaScript, and static error page
  templates/     Jinja templates
config.py        Application configuration profiles
extensions.py    Shared Flask extension instances
migrations/      Alembic migration configuration and history
tests/           Application and workflow tests
run.py           Dotenv loading and Flask application entry point
```

The application factory and CLI commands are in `app/__init__.py`. The
supported account roles are `student`, `supervisor`, `industry_supervisor`,
`university_supervisor`, `school_supervisor`, and `admin`.

## Security and deployment

- Replace the development `SECRET_KEY` with a long, unique secret.
- Use `FLASK_CONFIG=production` in production. It disables debug mode and
  requires secure session cookies; serve the app over HTTPS.
- Keep `.env`, SMTP credentials, and production database credentials out of
  version control.
- Provision administrator and supervisor accounts only through trusted
  administrative channels.
- Flask's built-in development server is for local development only.

### Deploying to PythonAnywhere

The production site is hosted at
[siwes360.pythonanywhere.com](https://siwes360.pythonanywhere.com/). To deploy
an update from GitHub, pull the intended branch in a PythonAnywhere Bash
console, activate the web app's virtual environment, install any updated
requirements, and apply pending migrations:

```bash
git pull origin main
pip install -r requirements.txt
flask --app run.py db upgrade
```

In the PythonAnywhere **Web** tab, confirm the source-code and virtual
environment paths, and set the WSGI configuration to import the Flask
application from this project, for example:

```python
from run import app as application
```

Set `FLASK_CONFIG=production`, a unique `SECRET_KEY`, and a persistent
`DATABASE_URL` in the web app's environment. Keep these values private. Reload
the web app from the **Web** tab after updating code or configuration. Pushing
to GitHub alone does not update the running site unless automatic deployment
has separately been configured.
