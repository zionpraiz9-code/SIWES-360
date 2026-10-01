import pytest

from app import create_app
from extensions import db
from models import User


@pytest.fixture
def app():
    app = create_app("config.TestingConfig")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_register_and_login_success(client):
    response = client.post(
        "/auth/register",
        data={
            "name": "Alice Student",
            "email": "alice@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "role": "student",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")

    user = User.query.filter_by(email="alice@example.com").first()
    assert user is not None
    assert user.password_hash != "StrongPass123!"
    assert user.role == "student"

    login_response = client.post(
        "/auth/login",
        data={"email": "alice@example.com", "password": "StrongPass123!"},
        follow_redirects=False,
    )

    assert login_response.status_code == 302
    assert login_response.headers["Location"].endswith("/dashboard")


def test_duplicate_email_registration_is_rejected(client):
    client.post(
        "/auth/register",
        data={
            "name": "First User",
            "email": "same@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "role": "student",
        },
        follow_redirects=False,
    )

    response = client.post(
        "/auth/register",
        data={
            "name": "Second User",
            "email": "same@example.com",
            "password": "StrongPass123!",
            "confirm_password": "StrongPass123!",
            "role": "student",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"already registered" in response.data.lower()
    assert User.query.filter_by(email="same@example.com").count() == 1


def test_login_fails_for_wrong_password_and_inactive_account(client):
    user = User(
        name="Inactive User",
        email="inactive@example.com",
        role="student",
        is_active=False,
    )
    user.set_password("StrongPass123!")
    db.session.add(user)
    db.session.commit()

    response = client.post(
        "/auth/login",
        data={"email": "inactive@example.com", "password": "WrongPass"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"invalid email or password" in response.data.lower()

    response = client.post(
        "/auth/login",
        data={"email": "inactive@example.com", "password": "StrongPass123!"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"inactive" in response.data.lower()


def test_logout_clears_session(client):
    user = User(name="Logout User", email="logout@example.com", role="student")
    user.set_password("StrongPass123!")
    db.session.add(user)
    db.session.commit()

    client.post(
        "/auth/login",
        data={"email": "logout@example.com", "password": "StrongPass123!"},
        follow_redirects=False,
    )

    response = client.get("/auth/logout", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")

    get_response = client.get("/dashboard", follow_redirects=False)
    assert get_response.status_code == 302
    assert get_response.headers["Location"].endswith("/auth/login")


def test_protected_routes_require_login(client):
    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/auth/login")


def test_student_cannot_access_admin_dashboard(client):
    user = User(name="Student User", email="student2@example.com", role="student")
    user.set_password("StrongPass123!")
    db.session.add(user)
    db.session.commit()

    client.post(
        "/auth/login",
        data={"email": "student2@example.com", "password": "StrongPass123!"},
        follow_redirects=False,
    )

    response = client.get("/admin/dashboard", follow_redirects=False)
    assert response.status_code == 403


def test_role_specific_dashboard_redirect(client):
    user = User(name="Supervisor User", email="supervisor@example.com", role="industry_supervisor")
    user.set_password("StrongPass123!")
    db.session.add(user)
    db.session.commit()

    client.post(
        "/auth/login",
        data={"email": "supervisor@example.com", "password": "StrongPass123!"},
        follow_redirects=False,
    )

    response = client.get("/dashboard", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/industry/dashboard")
