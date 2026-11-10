import re
import unittest
from datetime import date, timedelta

from app import create_app
from app.models import Attendance, DailyLog, StudentProfile, User, WeeklyReport
from extensions import db


class StudentDashboardTests(unittest.TestCase):
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
            user = User(
                full_name="Test Student",
                email="student@example.com",
                role="student",
            )
            user.set_password("StrongPass123")
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id

        self.client.post(
            "/auth/login",
            data={
                "email": "student@example.com",
                "password": "StrongPass123",
            },
        )

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()

    def test_dashboard_displays_live_student_metrics_and_recent_logs(self):
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        with self.app.app_context():
            db.session.add(
                StudentProfile(
                    user_id=self.user_id,
                    placement_start_date=week_start,
                )
            )
            db.session.add_all(
                [
                    Attendance(
                        user_id=self.user_id,
                        attendance_date=week_start,
                        status="present",
                    ),
                    DailyLog(
                        user_id=self.user_id,
                        log_date=today,
                        title="Latest activity",
                        activities="Completed a supervised training task.",
                    ),
                    DailyLog(
                        user_id=self.user_id,
                        log_date=week_start,
                        title="Earlier activity",
                        activities="Reviewed the workshop safety procedures.",
                        status="Approved",
                        supervisor_feedback="Well done.",
                    ),
                    WeeklyReport(
                        user_id=self.user_id,
                        week_start=week_start,
                        summary="Completed the assigned tasks and practiced new skills.",
                    ),
                ]
            )
            db.session.commit()

        response = self.client.get("/student/dashboard")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"20", response.data)
        self.assertIn(b"2", response.data)
        self.assertIn(b"Pending", response.data)
        self.assertIn(b"1", response.data)
        self.assertIn(b"Latest activity", response.data)
        self.assertIn(b"Earlier activity", response.data)
        self.assertIn(b"New log entry", response.data)
        self.assertIn(b"Mark attendance", response.data)
        self.assertIn(b"Submit weekly report", response.data)

    def test_full_report_includes_profile_and_chronological_logs_only_for_student(self):
        with self.app.app_context():
            db.session.add(
                StudentProfile(
                    user_id=self.user_id,
                    matric_number="SIWES/2026/010",
                    department="Computer Science",
                    company_name="Example Engineering Ltd",
                    company_address="12 Training Road, Lagos",
                    supervisor_name="Ada Supervisor",
                    supervisor_email="ada@example.com",
                    supervisor_phone="+234 800 000 0000",
                    school_supervisor_email="school@example.com",
                    start_date=date(2026, 1, 5),
                    end_date=date(2026, 4, 5),
                )
            )
            other_student = User(
                full_name="Other Student",
                email="other@example.com",
                role="student",
            )
            other_student.set_password("StrongPass123")
            db.session.add(other_student)
            db.session.flush()
            db.session.add_all(
                [
                    DailyLog(
                        user_id=self.user_id,
                        log_date=date(2026, 2, 2),
                        title="Second Activity",
                        activities="Completed a scheduled equipment inspection.",
                        tools_used="Inspection checklist",
                        skills_learned="Equipment inspection",
                        challenges_encountered="Limited access to the workshop.",
                        supervisor_feedback="Well documented.",
                    ),
                    DailyLog(
                        user_id=self.user_id,
                        log_date=date(2026, 1, 12),
                        title="First Activity",
                        activities="Completed workplace orientation.",
                    ),
                    DailyLog(
                        user_id=other_student.id,
                        log_date=date(2026, 1, 10),
                        title="Private Other Activity",
                        activities="This entry belongs to another student.",
                    ),
                ]
            )
            db.session.commit()

        response = self.client.get("/student/full-report")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Industrial Training Report", response.data)
        self.assertIn(b"SIWES/2026/010", response.data)
        self.assertIn(b"Example Engineering Ltd", response.data)
        self.assertIn(b"Inspection checklist", response.data)
        self.assertIn(b"Save as PDF / Print Report", response.data)
        self.assertIn(b"window.print()", response.data)
        self.assertNotIn(b"Private Other Activity", response.data)
        self.assertLess(
            response.data.index(b"First Activity"),
            response.data.index(b"Second Activity"),
        )
        self.assertIn(b"@media print", response.data)
        self.assertIn(b".site-header", response.data)

    def test_full_report_requires_login_and_student_role(self):
        self.client.post("/auth/logout")
        anonymous_response = self.client.get("/student/full-report")
        self.assertEqual(anonymous_response.status_code, 302)
        self.assertIn("/auth/login", anonymous_response.headers["Location"])

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
        response = self.client.get("/student/full-report")

        self.assertEqual(response.status_code, 403)

    def test_student_actions_persist_records_and_allow_attendance_updates(self):
        today = date.today()
        log_response = self.client.post(
            "/student/logs/new",
            data={
                "title": "Training orientation",
                "log_date": today.isoformat(),
                "activities": "Reviewed the orientation and safety procedures.",
            },
            follow_redirects=True,
        )
        attendance_response = self.client.post(
            "/student/attendance/mark",
            data={
                "attendance_date": today.isoformat(),
                "status": "present",
            },
            follow_redirects=True,
        )
        update_response = self.client.post(
            "/student/attendance/mark",
            data={
                "attendance_date": today.isoformat(),
                "status": "absent",
            },
            follow_redirects=True,
        )
        report_response = self.client.post(
            "/student/reports/weekly",
            data={"summary": "Completed the assigned tasks and learned new skills."},
            follow_redirects=True,
        )

        for response in (
            log_response,
            attendance_response,
            update_response,
            report_response,
        ):
            self.assertEqual(response.status_code, 200)

        with self.app.app_context():
            self.assertEqual(DailyLog.query.filter_by(user_id=self.user_id).count(), 1)
            attendance = Attendance.query.filter_by(
                user_id=self.user_id,
                attendance_date=today,
            ).one()
            self.assertEqual(attendance.status, "absent")
            self.assertEqual(
                WeeklyReport.query.filter_by(user_id=self.user_id).count(),
                1,
            )

    def test_weekly_reports_create_update_and_render_student_report(self):
        week_number = date.today().isocalendar().week
        payload = {
            "week_number": str(week_number),
            "summary": "Completed inventory and equipment checks.",
            "challenges_encountered": "A device needed troubleshooting.",
            "plans_for_next_week": "Practice preventive maintenance.",
        }
        first_response = self.client.post(
            "/student/weekly-reports",
            data=payload,
            follow_redirects=True,
        )
        self.assertEqual(first_response.status_code, 200)
        self.assertIn(b"Weekly Reports", first_response.data)
        self.assertIn(b"Completed inventory and equipment checks.", first_response.data)
        self.assertIn(b"Pending review", first_response.data)

        updated_response = self.client.post(
            "/student/weekly-reports",
            data={
                **payload,
                "summary": "Completed updated inventory checks.",
            },
            follow_redirects=True,
        )
        self.assertEqual(updated_response.status_code, 200)

        with self.app.app_context():
            reports = WeeklyReport.query.filter_by(user_id=self.user_id).all()
            self.assertEqual(len(reports), 1)
            report = reports[0]
            self.assertEqual(
                report.week_start,
                date.fromisocalendar(date.today().isocalendar().year, week_number, 1),
            )
            self.assertEqual(report.summary, "Completed updated inventory checks.")
            self.assertEqual(
                report.challenges_encountered,
                "A device needed troubleshooting.",
            )
            self.assertEqual(
                report.plans_for_next_week,
                "Practice preventive maintenance.",
            )
            self.assertIsNotNone(
                StudentProfile.query.filter_by(user_id=self.user_id).one()
            )

    def test_weekly_report_rejects_future_week_and_requires_all_report_fields(self):
        current_week = date.today().isocalendar().week
        response = self.client.post(
            "/student/weekly-reports",
            data={
                "week_number": str(current_week + 1),
                "summary": "Work completed.",
                "challenges_encountered": "None.",
                "plans_for_next_week": "Continue training.",
            },
        )

        self.assertEqual(response.status_code, 400)
        with self.app.app_context():
            self.assertEqual(
                WeeklyReport.query.filter_by(user_id=self.user_id).count(),
                0,
            )

        missing_fields_response = self.client.post(
            "/student/weekly-reports",
            data={"week_number": str(current_week), "summary": "Work completed."},
        )
        self.assertEqual(missing_fields_response.status_code, 400)

    def test_weekly_report_requires_login_and_student_role(self):
        self.client.post("/auth/logout")
        self.assertEqual(self.client.get("/student/weekly-reports").status_code, 302)

        with self.app.app_context():
            supervisor = User(
                full_name="Weekly Report Supervisor",
                email="weekly-supervisor@example.com",
                role="industry_supervisor",
            )
            supervisor.set_password("StrongPass123")
            db.session.add(supervisor)
            db.session.commit()

        self.client.post(
            "/auth/login",
            data={
                "email": "weekly-supervisor@example.com",
                "password": "StrongPass123",
            },
        )
        self.assertEqual(self.client.get("/student/weekly-reports").status_code, 403)

    def test_placement_details_create_update_and_prefill_profile(self):
        placement_data = {
            "company_name": "SIWES Technology Ltd",
            "company_address": "12 Innovation Road, Lagos",
            "supervisor_name": "Ada Supervisor",
            "supervisor_email": "ada.supervisor@example.com",
            "supervisor_phone": "+234 800 123 4567",
            "start_date": "2026-01-05",
            "end_date": "2026-06-30",
        }
        response = self.client.post(
            "/student/placement",
            data=placement_data,
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Your industrial placement details have been saved.", response.data)
        self.assertIn(b"SIWES Technology Ltd", response.data)
        with self.app.app_context():
            profile = StudentProfile.query.filter_by(user_id=self.user_id).one()
            self.assertEqual(profile.company_name, "SIWES Technology Ltd")
            self.assertEqual(profile.company_address, "12 Innovation Road, Lagos")
            self.assertEqual(profile.supervisor_name, "Ada Supervisor")
            self.assertEqual(profile.supervisor_email, "ada.supervisor@example.com")
            self.assertEqual(profile.supervisor_phone, "+234 800 123 4567")
            self.assertEqual(profile.start_date, date(2026, 1, 5))
            self.assertEqual(profile.placement_start_date, date(2026, 1, 5))
            self.assertEqual(profile.end_date, date(2026, 6, 30))

        updated_response = self.client.post(
            "/student/placement",
            data={**placement_data, "company_name": "Updated SIWES Ltd"},
            follow_redirects=True,
        )
        self.assertEqual(updated_response.status_code, 200)
        self.assertIn(b"Updated SIWES Ltd", updated_response.data)
        with self.app.app_context():
            self.assertEqual(
                StudentProfile.query.filter_by(user_id=self.user_id).count(),
                1,
            )

        get_response = self.client.get("/student/placement")
        self.assertEqual(get_response.status_code, 200)
        self.assertIn(b'value="Updated SIWES Ltd"', get_response.data)
        self.assertIn(b'value="ada.supervisor@example.com"', get_response.data)

    def test_placement_details_reject_invalid_email_dates_and_missing_fields(self):
        base_data = {
            "company_name": "Placement Company",
            "company_address": "1 Training Way",
            "supervisor_name": "Training Supervisor",
            "supervisor_email": "not-an-email",
            "supervisor_phone": "08000000000",
            "start_date": "2026-06-30",
            "end_date": "2026-01-05",
        }
        response = self.client.post("/student/placement", data=base_data)

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"valid email address", response.data.lower())
        self.assertIn(b"end date must be on or after", response.data.lower())
        with self.app.app_context():
            self.assertIsNone(
                StudentProfile.query.filter_by(user_id=self.user_id).first()
            )

        missing_field_response = self.client.post(
            "/student/placement",
            data={
                **base_data,
                "supervisor_email": "supervisor@example.com",
                "end_date": "2026-07-01",
                "company_name": " ",
            },
        )
        self.assertEqual(missing_field_response.status_code, 400)

    def test_placement_details_requires_login_and_student_role(self):
        self.client.post("/auth/logout")
        self.assertEqual(self.client.get("/student/placement").status_code, 302)

        with self.app.app_context():
            supervisor = User(
                full_name="Placement Supervisor",
                email="placement-supervisor@example.com",
                role="industry_supervisor",
            )
            supervisor.set_password("StrongPass123")
            db.session.add(supervisor)
            db.session.commit()

        self.client.post(
            "/auth/login",
            data={
                "email": "placement-supervisor@example.com",
                "password": "StrongPass123",
            },
        )
        self.assertEqual(self.client.get("/student/placement").status_code, 403)

    def test_future_attendance_date_is_rejected(self):
        response = self.client.post(
            "/student/attendance/mark",
            data={
                "attendance_date": (date.today() + timedelta(days=1)).isoformat(),
                "status": "present",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"not in the future", response.data)

    def test_logbook_creates_and_lists_student_daily_logs(self):
        response = self.client.post(
            "/student/logbook",
            data={
                "log_date": date.today().isoformat(),
                "title": "Network maintenance",
                "activities": "Inspected and configured office network equipment.",
                "tools_used": "Router console, cable tester",
                "skills_learned": "Network troubleshooting",
                "challenges_encountered": "Identified a damaged patch cable.",
            },
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Digital Logbook", response.data)
        self.assertIn(b"Network maintenance", response.data)
        self.assertIn(b"Router console, cable tester", response.data)
        self.assertIn(b"Pending", response.data)
        with self.app.app_context():
            log = DailyLog.query.filter_by(user_id=self.user_id).one()
            self.assertEqual(log.activities, "Inspected and configured office network equipment.")
            self.assertEqual(log.skills_learned, "Network troubleshooting")
            self.assertEqual(log.challenges_encountered, "Identified a damaged patch cable.")
            self.assertEqual(log.status, "Pending")
            self.assertIsNotNone(
                StudentProfile.query.filter_by(user_id=self.user_id).one()
            )

    def test_logbook_rejects_future_dates_and_invalid_fields(self):
        response = self.client.post(
            "/student/logbook",
            data={
                "log_date": (date.today() + timedelta(days=1)).isoformat(),
                "title": "Future activity",
                "activities": "This date must not be accepted.",
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn(b"cannot be in the future", response.data)
        with self.app.app_context():
            self.assertEqual(DailyLog.query.filter_by(user_id=self.user_id).count(), 0)

    def test_logbook_displays_approved_status_and_submission_date(self):
        with self.app.app_context():
            db.session.add(
                DailyLog(
                    user_id=self.user_id,
                    log_date=date.today(),
                    title="Reviewed activity",
                    activities="Completed the review.",
                    tools_used="Checklist",
                    status="Approved",
                )
            )
            db.session.commit()

        response = self.client.get("/student/logbook")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Reviewed activity", response.data)
        self.assertIn(b"Approved", response.data)
        self.assertIn(b"Checklist", response.data)
        self.assertIn(b"Submitted", response.data)

    def test_logbook_requires_authentication_and_is_student_only(self):
        self.client.post("/auth/logout")
        self.assertEqual(self.client.get("/student/logbook").status_code, 302)

        with self.app.app_context():
            supervisor = User(
                full_name="Test Supervisor",
                email="supervisor@example.com",
                role="industry_supervisor",
            )
            supervisor.set_password("StrongPass123")
            db.session.add(supervisor)
            db.session.commit()

        self.client.post(
            "/auth/login",
            data={
                "email": "supervisor@example.com",
                "password": "StrongPass123",
            },
        )
        self.assertEqual(self.client.get("/student/logbook").status_code, 403)

    def test_logbook_post_requires_a_valid_csrf_token(self):
        self.app.config["WTF_CSRF_ENABLED"] = True
        page = self.client.get("/student/logbook")
        token = re.search(rb'name="csrf_token" value="([^"]+)"', page.data)
        self.assertIsNotNone(token)

        payload = {
            "log_date": date.today().isoformat(),
            "title": "CSRF protected activity",
            "activities": "Submitted with the valid session token.",
        }
        rejected = self.client.post("/student/logbook", data=payload)
        accepted = self.client.post(
            "/student/logbook",
            data={**payload, "csrf_token": token.group(1).decode()},
        )

        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(accepted.status_code, 302)

    def test_weekday_calculation_counts_only_monday_through_friday(self):
        from app.main.routes import _weekdays_between

        self.assertEqual(
            _weekdays_between(date(2026, 10, 26), date(2026, 11, 1)),
            5,
        )
        self.assertEqual(
            _weekdays_between(date(2026, 10, 31), date(2026, 10, 30)),
            0,
        )


if __name__ == "__main__":
    unittest.main()
