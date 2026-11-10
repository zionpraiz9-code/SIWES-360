import unittest
from datetime import date, datetime
from unittest.mock import patch

from app import create_app
from app.models import DailyLog, StudentProfile, User, WeeklyReport
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

    def test_theme_toggle_and_assets_are_available_globally(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"data-theme-toggle", response.data)
        self.assertIn(b"js/theme.js", response.data)
        self.assertIn(b"css/theme.css", response.data)

        theme_script = self.client.get("/static/js/theme.js")
        theme_styles = self.client.get("/static/css/theme.css")
        self.assertEqual(theme_script.status_code, 200)
        self.assertIn(b"siwes360-theme", theme_script.data)
        self.assertEqual(theme_styles.status_code, 200)
        self.assertIn(b"#0b0f19", theme_styles.data)
        self.assertIn(b".glass-card:hover", theme_styles.data)

    def test_student_profile_declares_all_required_fields(self):
        required_fields = {
            "matric_number",
            "department",
            "company_name",
            "company_address",
            "supervisor_name",
            "supervisor_email",
            "supervisor_phone",
            "school_supervisor_email",
            "academic_score",
            "school_supervisor_comment",
            "start_date",
            "end_date",
        }

        self.assertTrue(required_fields.issubset(StudentProfile.__table__.columns.keys()))

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
        self.assertIn(b'<header class="site-header sticky-top">', response.data)
        self.assertIn(b'class="navbar container navbar-glass"', response.data)
        self.assertIn(b'href="/auth/login"', response.data)
        self.assertIn(b'href="/auth/register"', response.data)
        self.assertNotIn(b"Daily Logbook", response.data)
        self.assertNotIn(b"Privacy Policy", response.data)

    def test_each_role_gets_its_dashboard_and_account_links(self):
        dashboards = {
            "student": "/student/dashboard",
            "supervisor": "/supervisor/dashboard",
            "industry_supervisor": "/industry-supervisor/dashboard",
            "university_supervisor": "/university-supervisor/dashboard",
            "school_supervisor": "/school-supervisor/dashboard",
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

    def test_supervisor_dashboard_lists_only_profiles_assigned_by_email(self):
        supervisor_email = "ibs@example.com"
        with self.app.app_context():
            supervisor = User(
                full_name="Industrial Supervisor",
                email=supervisor_email,
                role="supervisor",
            )
            supervisor.set_password("StrongPass123")
            assigned_student = User(
                full_name="Assigned Student",
                email="assigned@example.com",
                role="student",
            )
            assigned_student.set_password("StrongPass123")
            other_student = User(
                full_name="Other Student",
                email="other@example.com",
                role="student",
            )
            other_student.set_password("StrongPass123")
            db.session.add_all([supervisor, assigned_student, other_student])
            db.session.flush()
            db.session.add_all(
                [
                    StudentProfile(
                        user_id=assigned_student.id,
                        matric_number="SIWES/2026/001",
                        department="Computer Science",
                        company_name="Assigned Company",
                        supervisor_email="IBS@EXAMPLE.COM",
                    ),
                    StudentProfile(
                        user_id=other_student.id,
                        company_name="Other Company",
                        supervisor_email="someone-else@example.com",
                    ),
                ]
            )
            db.session.commit()

        login_response = self.client.post(
            "/auth/login",
            data={
                "email": supervisor_email,
                "password": "StrongPass123",
            },
            follow_redirects=True,
        )
        self.assertEqual(login_response.status_code, 200)
        self.assertIn(b"Assigned Student", login_response.data)
        self.assertIn(b"SIWES/2026/001", login_response.data)
        self.assertIn(b"Computer Science", login_response.data)
        self.assertIn(b"Assigned Company", login_response.data)
        self.assertIn(b"Review Logs", login_response.data)
        self.assertNotIn(b"Other Student", login_response.data)
        self.assertNotIn(b"Other Company", login_response.data)

    def test_supervisor_dashboard_shows_log_metrics_and_student_progress(self):
        supervisor_email = "ibs@example.com"
        with self.app.app_context():
            supervisor = User(
                full_name="Industrial Supervisor",
                email=supervisor_email,
                role="supervisor",
            )
            supervisor.set_password("StrongPass123")
            student_with_logs = User(
                full_name="Student With Logs",
                email="logs@example.com",
                role="student",
            )
            student_without_logs = User(
                full_name="Student Without Logs",
                email="empty@example.com",
                role="student",
            )
            student_with_logs.set_password("StrongPass123")
            student_without_logs.set_password("StrongPass123")
            db.session.add_all(
                [supervisor, student_with_logs, student_without_logs]
            )
            db.session.flush()
            db.session.add_all(
                [
                    StudentProfile(
                        user_id=student_with_logs.id,
                        supervisor_email=supervisor_email,
                    ),
                    StudentProfile(
                        user_id=student_without_logs.id,
                        supervisor_email=supervisor_email,
                    ),
                    DailyLog(
                        user_id=student_with_logs.id,
                        title="Approved log",
                        activities="Approved activity",
                        status="Approved",
                    ),
                    DailyLog(
                        user_id=student_with_logs.id,
                        title="Pending log",
                        activities="Pending activity",
                        status="Pending",
                    ),
                    DailyLog(
                        user_id=student_with_logs.id,
                        title="Rejected log",
                        activities="Rejected activity",
                        status="Rejected",
                    ),
                ]
            )
            db.session.commit()

        self.client.post(
            "/auth/login",
            data={
                "email": supervisor_email,
                "password": "StrongPass123",
            },
        )
        response = self.client.get("/supervisor/dashboard")

        self.assertEqual(response.status_code, 200)
        for expected in (
            b"ASSIGNED INTERNS",
            b"PENDING LOGS",
            b"APPROVED REVIEWS",
            b"APPROVAL RATE",
            b">2</p>",
            b">1</p>",
            b"33.3",
            b"1 rejection",
            b"Student With Logs",
            b"1 of 3 approved",
            b"33.3%",
            b"Student Without Logs",
            b"0 of 0 approved",
        ):
            self.assertIn(expected, response.data)

    def test_admin_dashboard_shows_system_metrics_and_assigns_supervisors(self):
        admin = User(
            full_name="System Admin",
            email="admin@example.com",
            role="admin",
        )
        admin.set_password("StrongPass123")
        student = User(
            full_name="Admin Student",
            email="adminstudent@example.com",
            role="student",
        )
        student.set_password("StrongPass123")
        supervisor = User(
            full_name="Industrial Supervisor",
            email="industry@example.com",
            role="supervisor",
        )
        supervisor.set_password("StrongPass123")
        school_supervisor = User(
            full_name="School Supervisor",
            email="school@example.com",
            role="school_supervisor",
        )
        school_supervisor.set_password("StrongPass123")
        with self.app.app_context():
            db.session.add_all([admin, student, supervisor, school_supervisor])
            db.session.flush()
            db.session.add(
                StudentProfile(
                    user_id=student.id,
                    matric_number="SIWES/2026/030",
                    department="Computer Science",
                    company_name="Placement Company",
                )
            )
            db.session.commit()
            student_id = student.id

        self.client.post(
            "/auth/login",
            data={"email": "admin@example.com", "password": "StrongPass123"},
        )
        dashboard = self.client.get("/admin/dashboard")

        self.assertEqual(dashboard.status_code, 200)
        for expected in (
            b"TOTAL USERS",
            b"STUDENTS",
            b"SUPERVISORS",
            b"STUDENTS WITH ASSIGNMENTS",
            b"User management",
            b"Create a user account",
            b'name="username"',
            b'name="email"',
            b'name="password"',
            b"Admin Student",
            b"SIWES/2026/030",
            b"Current role",
            b'name="role"',
            b'name="supervisor_email"',
            b'name="school_supervisor_email"',
        ):
            self.assertIn(expected, dashboard.data)

        response = self.client.post(
            f"/admin/allocate-supervisor/{student_id}",
            data={
                "supervisor_email": " INDUSTRY@EXAMPLE.COM ",
                "school_supervisor_email": "School@Example.com",
            },
        )

        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            profile = StudentProfile.query.filter_by(user_id=student_id).one()
            self.assertEqual(profile.supervisor_email, "industry@example.com")
            self.assertEqual(
                profile.school_supervisor_email,
                "school@example.com",
            )

    def test_admin_can_create_user_with_hashed_password_and_selected_role(self):
        with self.app.app_context():
            admin = User(
                full_name="System Admin",
                email="admin@example.com",
                role="admin",
            )
            admin.set_password("StrongPass123")
            db.session.add(admin)
            db.session.commit()

        self.client.post(
            "/auth/login",
            data={"email": "admin@example.com", "password": "StrongPass123"},
        )
        response = self.client.post(
            "/admin/create-user",
            data={
                "username": "Industrial Supervisor",
                "email": "SUPERVISOR@EXAMPLE.COM",
                "password": "TemporaryPass123",
                "role": "supervisor",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Account created for Industrial Supervisor.", response.data)
        with self.app.app_context():
            user = User.query.filter_by(email="supervisor@example.com").one()
            self.assertEqual(user.full_name, "Industrial Supervisor")
            self.assertEqual(user.role, "supervisor")
            self.assertNotEqual(user.password_hash, "TemporaryPass123")
            self.assertTrue(user.check_password("TemporaryPass123"))

    def test_non_admin_cannot_create_users(self):
        with self.app.app_context():
            student = User(
                full_name="Test Student",
                email="student@example.com",
                role="student",
            )
            student.set_password("StrongPass123")
            db.session.add(student)
            db.session.commit()

        self.client.post(
            "/auth/login",
            data={"email": "student@example.com", "password": "StrongPass123"},
        )
        response = self.client.post(
            "/admin/create-user",
            data={
                "username": "Injected Admin",
                "email": "injected@example.com",
                "password": "TemporaryPass123",
                "role": "admin",
            },
        )

        self.assertEqual(response.status_code, 403)
        with self.app.app_context():
            self.assertIsNone(User.query.filter_by(email="injected@example.com").first())

    def test_anonymous_user_is_redirected_from_user_creation(self):
        response = self.client.post("/admin/create-user")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/auth/login", response.headers["Location"])

    def test_admin_user_creation_rejects_duplicate_email_and_unlisted_role(self):
        with self.app.app_context():
            admin = User(
                full_name="System Admin",
                email="admin@example.com",
                role="admin",
            )
            admin.set_password("StrongPass123")
            existing = User(
                full_name="Existing User",
                email="taken@example.com",
                role="student",
            )
            existing.set_password("StrongPass123")
            db.session.add_all([admin, existing])
            db.session.commit()

        self.client.post(
            "/auth/login",
            data={"email": "admin@example.com", "password": "StrongPass123"},
        )
        duplicate_response = self.client.post(
            "/admin/create-user",
            data={
                "username": "Duplicate User",
                "email": "TAKEN@example.com",
                "password": "TemporaryPass123",
                "role": "student",
            },
        )
        invalid_role_response = self.client.post(
            "/admin/create-user",
            data={
                "username": "Invalid Role",
                "email": "invalid-role@example.com",
                "password": "TemporaryPass123",
                "role": "industry_supervisor",
            },
        )

        self.assertEqual(duplicate_response.status_code, 409)
        self.assertIn(b"already exists", duplicate_response.data)
        self.assertEqual(invalid_role_response.status_code, 400)
        with self.app.app_context():
            self.assertEqual(User.query.count(), 2)

    def test_admin_can_update_user_role_from_allowed_roles(self):
        with self.app.app_context():
            admin = User(
                full_name="System Admin",
                email="admin@example.com",
                role="admin",
            )
            admin.set_password("StrongPass123")
            student = User(
                full_name="Role Change Student",
                email="rolechange@example.com",
                role="student",
            )
            student.set_password("StrongPass123")
            db.session.add_all([admin, student])
            db.session.commit()
            student_id = student.id

        self.client.post(
            "/auth/login",
            data={"email": "admin@example.com", "password": "StrongPass123"},
        )
        response = self.client.post(
            f"/admin/update-role/{student_id}",
            data={"role": "school_supervisor"},
        )

        self.assertEqual(response.status_code, 302)
        with self.app.app_context():
            user = db.session.get(User, student_id)
            self.assertEqual(user.role, "school_supervisor")

    def test_admin_role_update_rejects_role_outside_allowed_list(self):
        with self.app.app_context():
            admin = User(
                full_name="System Admin",
                email="admin@example.com",
                role="admin",
            )
            admin.set_password("StrongPass123")
            student = User(
                full_name="Role Change Student",
                email="rolechange@example.com",
                role="student",
            )
            student.set_password("StrongPass123")
            db.session.add_all([admin, student])
            db.session.commit()
            student_id = student.id

        self.client.post(
            "/auth/login",
            data={"email": "admin@example.com", "password": "StrongPass123"},
        )
        response = self.client.post(
            f"/admin/update-role/{student_id}",
            data={"role": "industry_supervisor"},
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Choose a valid user role.", response.data)
        with self.app.app_context():
            user = db.session.get(User, student_id)
            self.assertEqual(user.role, "student")

    def test_admin_allocation_rejects_invalid_email_without_changing_assignments(self):
        with self.app.app_context():
            admin = User(
                full_name="System Admin",
                email="admin@example.com",
                role="admin",
            )
            admin.set_password("StrongPass123")
            student = User(
                full_name="Admin Student",
                email="adminstudent@example.com",
                role="student",
            )
            student.set_password("StrongPass123")
            db.session.add_all([admin, student])
            db.session.flush()
            db.session.add(
                StudentProfile(
                    user_id=student.id,
                    supervisor_email="existing@example.com",
                )
            )
            db.session.commit()
            student_id = student.id

        self.client.post(
            "/auth/login",
            data={"email": "admin@example.com", "password": "StrongPass123"},
        )
        response = self.client.post(
            f"/admin/allocate-supervisor/{student_id}",
            data={
                "supervisor_email": "not-an-email",
                "school_supervisor_email": "",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Enter a valid industrial supervisor email address.", response.data)
        with self.app.app_context():
            profile = StudentProfile.query.filter_by(user_id=student_id).one()
            self.assertEqual(profile.supervisor_email, "existing@example.com")
            self.assertIsNone(profile.school_supervisor_email)

    def test_non_admin_cannot_allocate_supervisors(self):
        with self.app.app_context():
            student = User(
                full_name="Regular Student",
                email="student@example.com",
                role="student",
            )
            student.set_password("StrongPass123")
            assigned_student = User(
                full_name="Assigned Student",
                email="assigned@example.com",
                role="student",
            )
            assigned_student.set_password("StrongPass123")
            db.session.add_all([student, assigned_student])
            db.session.flush()
            db.session.add(
                StudentProfile(
                    user_id=assigned_student.id,
                    supervisor_email="existing@example.com",
                )
            )
            db.session.commit()
            assigned_student_id = assigned_student.id

        self.client.post(
            "/auth/login",
            data={"email": "student@example.com", "password": "StrongPass123"},
        )
        response = self.client.post(
            f"/admin/allocate-supervisor/{assigned_student_id}",
            data={
                "supervisor_email": "new@example.com",
                "school_supervisor_email": "school@example.com",
            },
        )

        self.assertEqual(response.status_code, 403)
        with self.app.app_context():
            profile = StudentProfile.query.filter_by(
                user_id=assigned_student_id
            ).one()
            self.assertEqual(profile.supervisor_email, "existing@example.com")
            self.assertIsNone(profile.school_supervisor_email)

    def test_school_supervisor_dashboard_lists_only_assigned_students(self):
        supervisor_email = "lecturer@example.com"
        with self.app.app_context():
            supervisor = User(
                full_name="Academic Supervisor",
                email=supervisor_email,
                role="school_supervisor",
            )
            supervisor.set_password("StrongPass123")
            assigned_student = User(
                full_name="Assigned Student",
                email="assigned@example.com",
                role="student",
            )
            assigned_student.set_password("StrongPass123")
            other_student = User(
                full_name="Other Student",
                email="other@example.com",
                role="student",
            )
            other_student.set_password("StrongPass123")
            db.session.add_all([supervisor, assigned_student, other_student])
            db.session.flush()
            db.session.add_all(
                [
                    StudentProfile(
                        user_id=assigned_student.id,
                        matric_number="SIWES/2026/010",
                        department="Computer Science",
                        company_name="Assigned Company",
                        supervisor_email="industry@example.com",
                        school_supervisor_email="LECTURER@EXAMPLE.COM",
                        academic_score=87.5,
                        school_supervisor_comment="Excellent progress.",
                    ),
                    StudentProfile(
                        user_id=other_student.id,
                        school_supervisor_email="someone-else@example.com",
                    ),
                ]
            )
            db.session.commit()

        response = self.client.post(
            "/auth/login",
            data={
                "email": supervisor_email,
                "password": "StrongPass123",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Assigned Student", response.data)
        self.assertIn(b"SIWES/2026/010", response.data)
        self.assertIn(b"Computer Science", response.data)
        self.assertIn(b"Assigned Company", response.data)
        self.assertIn(b"industry@example.com", response.data)
        self.assertIn(b"87.5", response.data)
        self.assertIn(b"Excellent progress.", response.data)
        self.assertNotIn(b"Other Student", response.data)

    def test_non_school_supervisor_cannot_access_school_dashboard(self):
        with self.app.app_context():
            user = User(
                full_name="Regular Student",
                email="student@example.com",
                role="student",
            )
            user.set_password("StrongPass123")
            db.session.add(user)
            db.session.commit()

        self.client.post(
            "/auth/login",
            data={
                "email": "student@example.com",
                "password": "StrongPass123",
            },
        )

        response = self.client.get("/school-supervisor/dashboard")

        self.assertEqual(response.status_code, 403)

    def test_school_supervisor_can_inspect_and_grade_assigned_student(self):
        supervisor_email = "lecturer@example.com"
        with self.app.app_context():
            supervisor = User(
                full_name="Academic Supervisor",
                email=supervisor_email,
                role="school_supervisor",
            )
            supervisor.set_password("StrongPass123")
            student = User(
                full_name="Inspected Student",
                email="inspected@example.com",
                role="student",
            )
            student.set_password("StrongPass123")
            db.session.add_all([supervisor, student])
            db.session.flush()
            db.session.add(
                StudentProfile(
                    user_id=student.id,
                    matric_number="SIWES/2026/020",
                    department="Electrical Engineering",
                    company_name="Training Company",
                    supervisor_email="industry@example.com",
                    school_supervisor_email=supervisor_email,
                )
            )
            db.session.add_all(
                [
                    DailyLog(
                        user_id=student.id,
                        log_date=date.today(),
                        title="Built a prototype",
                        activities="Created a sensor prototype.",
                        status="Approved",
                        supervisor_comment="Good practical work.",
                    ),
                    WeeklyReport(
                        user_id=student.id,
                        week_start=date.today(),
                        summary="Completed prototype testing.",
                        status="Rejected",
                        supervisor_comment="Add more test details.",
                    ),
                ]
            )
            db.session.commit()
            student_id = student.id

        self.client.post(
            "/auth/login",
            data={
                "email": supervisor_email,
                "password": "StrongPass123",
            },
        )

        inspection = self.client.get(
            f"/school-supervisor/students/{student_id}/inspect"
        )

        self.assertEqual(inspection.status_code, 200)
        for expected in (
            b"SIWES/2026/020",
            b"Electrical Engineering",
            b"Training Company",
            b"industry@example.com",
            b"Built a prototype",
            b"Good practical work.",
            b"Rejected",
            b"Add more test details.",
            b'name="academic_score"',
            b'name="school_supervisor_comment"',
            b"Save Assessment",
        ):
            self.assertIn(expected, inspection.data)
        self.assertNotIn(b'name="status"', inspection.data)
        self.assertNotIn(b">Approve<", inspection.data)

        with patch("app.main.routes.mail.send") as send_mail:
            response = self.client.post(
                f"/school-supervisor/students/{student_id}/inspect",
                data={
                    "academic_score": "91.5",
                    "school_supervisor_comment": "Excellent technical progress.",
                },
            )

        self.assertEqual(response.status_code, 302)
        send_mail.assert_called_once()
        message = send_mail.call_args.args[0]
        self.assertEqual(message.recipients, ["inspected@example.com"])
        self.assertIn("91.5", message.body)
        self.assertIn("Excellent technical progress.", message.body)
        with self.app.app_context():
            profile = StudentProfile.query.filter_by(user_id=student_id).one()
            self.assertEqual(profile.academic_score, 91.5)
            self.assertEqual(
                profile.school_supervisor_comment,
                "Excellent technical progress.",
            )

    def test_school_assessment_is_saved_when_notification_email_fails(self):
        supervisor_email = "lecturer@example.com"
        with self.app.app_context():
            supervisor = User(
                full_name="Academic Supervisor",
                email=supervisor_email,
                role="school_supervisor",
            )
            supervisor.set_password("StrongPass123")
            student = User(
                full_name="Inspected Student",
                email="inspected@example.com",
                role="student",
            )
            student.set_password("StrongPass123")
            db.session.add_all([supervisor, student])
            db.session.flush()
            db.session.add(
                StudentProfile(
                    user_id=student.id,
                    school_supervisor_email=supervisor_email,
                )
            )
            db.session.commit()
            student_id = student.id

        self.client.post(
            "/auth/login",
            data={
                "email": supervisor_email,
                "password": "StrongPass123",
            },
        )
        with patch(
            "app.main.routes.mail.send",
            side_effect=RuntimeError("SMTP unavailable"),
        ):
            response = self.client.post(
                f"/school-supervisor/students/{student_id}/inspect",
                data={
                    "academic_score": "78",
                    "school_supervisor_comment": "Keep improving.",
                },
                follow_redirects=True,
            )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Academic assessment saved.", response.data)
        self.assertIn(b"notification email could not be sent", response.data)
        with self.app.app_context():
            profile = StudentProfile.query.filter_by(user_id=student_id).one()
            self.assertEqual(profile.academic_score, 78)
            self.assertEqual(profile.school_supervisor_comment, "Keep improving.")

    def test_school_supervisor_cannot_inspect_unassigned_student(self):
        with self.app.app_context():
            supervisor = User(
                full_name="Academic Supervisor",
                email="lecturer@example.com",
                role="school_supervisor",
            )
            supervisor.set_password("StrongPass123")
            student = User(
                full_name="Unassigned Student",
                email="unassigned@example.com",
                role="student",
            )
            student.set_password("StrongPass123")
            db.session.add_all([supervisor, student])
            db.session.flush()
            db.session.add(StudentProfile(user_id=student.id))
            db.session.commit()
            student_id = student.id

        self.client.post(
            "/auth/login",
            data={
                "email": "lecturer@example.com",
                "password": "StrongPass123",
            },
        )
        response = self.client.get(
            f"/school-supervisor/students/{student_id}/inspect"
        )

        self.assertEqual(response.status_code, 404)

    def test_non_school_supervisor_cannot_inspect_student(self):
        with self.app.app_context():
            student = User(
                full_name="Regular Student",
                email="student@example.com",
                role="student",
            )
            student.set_password("StrongPass123")
            db.session.add(student)
            db.session.flush()
            db.session.add(StudentProfile(user_id=student.id))
            db.session.commit()
            student_id = student.id

        self.client.post(
            "/auth/login",
            data={
                "email": "student@example.com",
                "password": "StrongPass123",
            },
        )
        response = self.client.get(
            f"/school-supervisor/students/{student_id}/inspect"
        )

        self.assertEqual(response.status_code, 403)

    def test_supervisor_can_review_logs_only_for_assigned_student(self):
        with self.app.app_context():
            supervisor = User(
                full_name="Industrial Supervisor",
                email="ibs@example.com",
                role="supervisor",
            )
            supervisor.set_password("StrongPass123")
            assigned_student = User(
                full_name="Assigned Student",
                email="assigned@example.com",
                role="student",
            )
            assigned_student.set_password("StrongPass123")
            unassigned_student = User(
                full_name="Unassigned Student",
                email="unassigned@example.com",
                role="student",
            )
            unassigned_student.set_password("StrongPass123")
            db.session.add_all([supervisor, assigned_student, unassigned_student])
            db.session.flush()
            db.session.add(
                StudentProfile(
                    user_id=assigned_student.id,
                    supervisor_email=supervisor.email,
                )
            )
            db.session.add_all(
                [
                    DailyLog(
                        user_id=assigned_student.id,
                        title="Assigned work",
                        activities="This log belongs to the assigned intern.",
                    ),
                    DailyLog(
                        user_id=unassigned_student.id,
                        title="Private work",
                        activities="This log must not be visible.",
                    ),
                ]
            )
            db.session.commit()
            assigned_id = assigned_student.id
            unassigned_id = unassigned_student.id
            assigned_log_id = DailyLog.query.filter_by(
                user_id=assigned_student.id,
            ).one().id

        self.client.post(
            "/auth/login",
            data={"email": "ibs@example.com", "password": "StrongPass123"},
        )
        response = self.client.get(f"/supervisor/students/{assigned_id}/logs")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Assigned work", response.data)
        self.assertNotIn(b"Private work", response.data)
        self.assertEqual(
            self.client.get(f"/supervisor/students/{unassigned_id}/logs").status_code,
            404,
        )
        review_response = self.client.post(
            f"/supervisor/students/{assigned_id}/logs/{assigned_log_id}/review",
            data={
                "status": "Rejected",
                "supervisor_comment": "Please include more detail about the task.",
            },
            follow_redirects=True,
        )
        self.assertEqual(review_response.status_code, 200)
        self.assertIn(b"Daily log rejected and revision requested.", review_response.data)
        self.assertIn(b"Rejected", review_response.data)
        self.assertIn(b"Please include more detail about the task.", review_response.data)
        with self.app.app_context():
            reviewed_log = db.session.get(DailyLog, assigned_log_id)
            self.assertEqual(reviewed_log.status, "Rejected")
            self.assertEqual(
                reviewed_log.supervisor_comment,
                "Please include more detail about the task.",
            )
            self.assertEqual(
                reviewed_log.supervisor_feedback,
                "Please include more detail about the task.",
            )

    def test_supervisor_log_review_rejects_invalid_actions_and_unassigned_logs(self):
        with self.app.app_context():
            supervisor = User(
                full_name="Assigned Supervisor",
                email="assigned-supervisor@example.com",
                role="supervisor",
            )
            supervisor.set_password("StrongPass123")
            student = User(
                full_name="Assigned Intern",
                email="intern@example.com",
                role="student",
            )
            student.set_password("StrongPass123")
            db.session.add_all([supervisor, student])
            db.session.flush()
            db.session.add(
                StudentProfile(
                    user_id=student.id,
                    supervisor_email=supervisor.email,
                )
            )
            log = DailyLog(
                user_id=student.id,
                title="Test log",
                activities="A training activity.",
            )
            db.session.add(log)
            db.session.commit()
            student_id = student.id
            log_id = log.id

        self.client.post(
            "/auth/login",
            data={
                "email": "assigned-supervisor@example.com",
                "password": "StrongPass123",
            },
        )
        invalid_action = self.client.post(
            f"/supervisor/students/{student_id}/logs/{log_id}/review",
            data={"status": "Pending", "supervisor_comment": ""},
        )
        too_long_comment = self.client.post(
            f"/supervisor/students/{student_id}/logs/{log_id}/review",
            data={"status": "Approved", "supervisor_comment": "x" * 5001},
        )

        self.assertEqual(invalid_action.status_code, 400)
        self.assertEqual(too_long_comment.status_code, 400)
        with self.app.app_context():
            self.assertEqual(db.session.get(DailyLog, log_id).status, "Pending")

    def test_supervisor_can_review_weekly_reports_only_for_assigned_student(self):
        from datetime import date, timedelta

        with self.app.app_context():
            supervisor = User(
                full_name="Weekly Report Supervisor",
                email="weekly-ibs@example.com",
                role="supervisor",
            )
            supervisor.set_password("StrongPass123")
            assigned_student = User(
                full_name="Weekly Report Intern",
                email="weekly-intern@example.com",
                role="student",
            )
            assigned_student.set_password("StrongPass123")
            other_student = User(
                full_name="Unassigned Weekly Intern",
                email="other-weekly-intern@example.com",
                role="student",
            )
            other_student.set_password("StrongPass123")
            db.session.add_all([supervisor, assigned_student, other_student])
            db.session.flush()
            db.session.add(
                StudentProfile(
                    user_id=assigned_student.id,
                    supervisor_email=supervisor.email,
                )
            )
            week_start = date.today() - timedelta(days=date.today().weekday())
            assigned_report = WeeklyReport(
                user_id=assigned_student.id,
                week_start=week_start,
                summary="Completed assigned tasks.",
                challenges_encountered="Equipment delay.",
                plans_for_next_week="Complete testing.",
            )
            unassigned_report = WeeklyReport(
                user_id=other_student.id,
                week_start=week_start,
                summary="Private report.",
            )
            db.session.add_all([assigned_report, unassigned_report])
            db.session.commit()
            student_id = assigned_student.id
            report_id = assigned_report.id
            unassigned_report_id = unassigned_report.id

        self.client.post(
            "/auth/login",
            data={
                "email": "weekly-ibs@example.com",
                "password": "StrongPass123",
            },
        )
        review_page = self.client.get(
            f"/supervisor/students/{student_id}/logs",
        )
        self.assertEqual(review_page.status_code, 200)
        self.assertIn(b"Weekly reports", review_page.data)
        self.assertIn(b"Completed assigned tasks.", review_page.data)
        self.assertIn(b"Reject / Request Revision", review_page.data)

        response = self.client.post(
            f"/supervisor/students/{student_id}/weekly-reports/{report_id}/review",
            data={
                "status": "Approved",
                "supervisor_comment": "Good progress this week.",
            },
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Weekly report approved.", response.data)
        self.assertIn(b"Good progress this week.", response.data)
        self.assertIn(b"Approved", response.data)
        self.assertEqual(
            self.client.post(
                f"/supervisor/students/{student_id}/weekly-reports/{unassigned_report_id}/review",
                data={"status": "Rejected"},
            ).status_code,
            404,
        )

        with self.app.app_context():
            report = db.session.get(WeeklyReport, report_id)
            self.assertEqual(report.status, "Approved")
            self.assertEqual(
                report.supervisor_comment,
                "Good progress this week.",
            )
            self.assertEqual(
                report.supervisor_feedback,
                "Good progress this week.",
            )


if __name__ == "__main__":
    unittest.main()
