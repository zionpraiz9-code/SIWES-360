import unittest
from datetime import datetime

from app import create_app
from app.models import User
from extensions import db


class ApplicationTests(unittest.TestCase):
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

    def test_factory_registers_health_endpoint(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {"status": "ok", "application": "SIWES360"},
        )

    def test_unknown_route_returns_not_found(self):
        response = self.client.get("/not-a-real-page")

        self.assertEqual(response.status_code, 404)

    def test_home_page_returns_success(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"SIWES", response.data)

    def test_public_footer_links_to_available_account_pages(self):
        response = self.client.get("/")

        self.assertIn(f"© {datetime.now().year} SIWES360".encode(), response.data)
        self.assertIn(b'href="/auth/login"', response.data)
        self.assertIn(b'href="/auth/register"', response.data)
        self.assertNotIn(b"Daily Logbook", response.data)
        self.assertNotIn(b"Privacy Policy", response.data)

    def test_each_role_gets_its_dashboard_and_account_links(self):
        dashboards = {
            "student": "/student/dashboard",
            "industry_supervisor": "/industry-supervisor/dashboard",
            "university_supervisor": "/university-supervisor/dashboard",
            "admin": "/admin/dashboard",
        }

        for index, (role, dashboard) in enumerate(dashboards.items()):
            if index:
                self.client.post("/auth/logout")
            with self.app.app_context():
                user = User(
                    full_name=f"Test {role}",
                    email=f"{role}@example.com",
                    role=role,
                )
                user.set_password("StrongPass123")
                db.session.add(user)
                db.session.commit()

            login_response = self.client.post(
                "/auth/login",
                data={
                    "email": f"{role}@example.com",
                    "password": "StrongPass123",
                },
                follow_redirects=True,
            )
            self.assertEqual(login_response.status_code, 200)
            self.assertIn(f'href="{dashboard}"'.encode(), login_response.data)
            self.assertIn(b'href="/auth/change-password"', login_response.data)
            self.assertNotIn(b"Create a student account", login_response.data)


if __name__ == "__main__":
    unittest.main()
