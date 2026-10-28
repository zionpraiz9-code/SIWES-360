import unittest

from app import create_app
from app.models import User
from extensions import db


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(
            {
                "TESTING": True,
                "SECRET_KEY": "test-secret-key",
                "SQLALCHEMY_DATABASE_URI": "sqlite://",
                "WTF_CSRF_ENABLED": False,
            }
        )
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def register(self, email="student@example.com", password="StrongPass123", **extra):
        with self.app.app_context():
            data = {
                "full_name": "Test Student",
                "email": email,
                "password": password,
                "confirm_password": password,
            }
            data.update(extra)
            return self.client.post("/auth/register", data=data, follow_redirects=True)

    def create_user(self, email="student@example.com", password="StrongPass123", role="student"):
        with self.app.app_context():
            user = User(
                full_name="Test User",
                email=email,
                role=role,
            )
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            return user

    def login(self, email="student@example.com", password="StrongPass123"):
        return self.client.post(
            "/auth/login",
            data={"email": email, "password": password},
            follow_redirects=True,
        )

    def test_successful_registration_stores_a_hash_and_student_role(self):
        response = self.register()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your student account was created", response.data)
        with self.app.app_context():
            user = User.query.filter_by(email="student@example.com").one()
            self.assertEqual(user.role, "student")
            self.assertNotEqual(user.password_hash, "StrongPass123")
            self.assertTrue(user.check_password("StrongPass123"))

    def test_duplicate_email_registration_is_rejected(self):
        self.register()
        response = self.register()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"already exists", response.data)
        with self.app.app_context():
            self.assertEqual(User.query.count(), 1)

    def test_successful_login(self):
        self.create_user()
        response = self.login()
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Welcome back, Test User.", response.data)

    def test_incorrect_password_is_rejected(self):
        self.create_user()
        response = self.login(password="wrong-password")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Email or password is incorrect.", response.data)
        self.assertNotIn(b"Welcome back, Test User.", response.data)

    def test_logout_clears_authenticated_session(self):
        self.create_user()
        self.login()
        response = self.client.post("/auth/logout", follow_redirects=True)
        self.assertIn(b"You have been logged out.", response.data)
        self.assertEqual(response.request.path, "/auth/login")
        protected_response = self.client.get("/student/dashboard")
        self.assertEqual(protected_response.status_code, 302)
        self.assertIn("/auth/login", protected_response.headers["Location"])

    def test_anonymous_user_is_redirected_from_protected_dashboard(self):
        response = self.client.get("/student/dashboard")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers["Location"])

    def test_student_cannot_access_admin_dashboard(self):
        self.create_user()
        self.login()
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 403)
        self.assertIn(b"not available to your account.", response.data)

    def test_supervisor_cannot_access_admin_dashboard(self):
        self.create_user(role="university_supervisor")
        self.login()
        response = self.client.get("/admin/dashboard")
        self.assertEqual(response.status_code, 403)

    def test_public_registration_cannot_assign_privileged_role(self):
        response = self.register(
            email="attacker@example.com",
            role="admin",
        )
        self.assertEqual(response.status_code, 200)
        with self.app.app_context():
            user = User.query.filter_by(email="attacker@example.com").one()
            self.assertEqual(user.role, "student")

    def test_logged_in_role_can_access_its_dashboard(self):
        self.create_user(role="industry_supervisor")
        self.login()
        response = self.client.get("/industry-supervisor/dashboard")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Industry Supervisor dashboard", response.data)

    def test_login_rejects_external_next_redirect(self):
        self.create_user()
        response = self.client.post(
            "/auth/login?next=https://example.com",
            data={"email": "student@example.com", "password": "StrongPass123"},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/student/dashboard")

    def test_invalid_role_is_rejected(self):
        with self.app.app_context():
            with self.assertRaises(ValueError):
                User(full_name="Invalid Role", email="bad@example.com", role="root")


    def test_password_change_requires_correct_current_password(self):
        self.create_user()
        self.login()
        response = self.client.post(
            "/auth/change-password",
            data={
                "current_password": "IncorrectPass123",
                "new_password": "AnotherPass456",
                "confirm_password": "AnotherPass456",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Current password is incorrect.", response.data)
        with self.app.app_context():
            user = User.query.filter_by(email="student@example.com").one()
            self.assertTrue(user.check_password("StrongPass123"))

    def test_password_change_updates_the_password_hash(self):
        self.create_user()
        self.login()
        response = self.client.post(
            "/auth/change-password",
            data={
                "current_password": "StrongPass123",
                "new_password": "AnotherPass456",
                "confirm_password": "AnotherPass456",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your password has been changed.", response.data)
        with self.app.app_context():
            user = User.query.filter_by(email="student@example.com").one()
            self.assertTrue(user.check_password("AnotherPass456"))


if __name__ == "__main__":
    unittest.main()
