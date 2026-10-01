# Learning log

## Phase 1

- Used a Flask application factory to keep app configuration modular and testable.
- Added Flask-Login so user sessions are managed centrally and can protect private routes consistently.
- Kept role checks in a reusable decorator rather than duplicating logic in each route.
- Used a safe redirect helper to block open redirects via the `next` query string.
- Added CSRF tokens to forms to preserve security even when route logic is extended later.
- Used separate config classes for development, testing, and production so the same code can run in local and CI environments.
