# SIWES360

SIWES360 is a Flask application for managing student SIWES placements, attendance, activities, reports, supervisor reviews, and admin oversight.

## Requirements

- Python 3.11+
- Virtual environment recommended

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Copy the sample environment file and update values if needed:
   `copy .env.example .env`
4. Start the app:
   `python run.py`

## Running the app

Use:

```bash
flask --app app run
```

Or the project runner:

```bash
python run.py
```

## Creating an admin account

```bash
flask --app app create-admin
```

The command will prompt for name, email, and password.

## Running tests

```bash
python -m pytest
```

## Phase 1 focus

This phase includes the project foundation, safe authentication, role-based access, protected dashboards, and CSRF-secured auth forms.
