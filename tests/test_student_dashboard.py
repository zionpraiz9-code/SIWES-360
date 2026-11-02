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
        self.assertIn(b"Submitted", response.data)
        self.assertIn(b"1", response.data)
        self.assertIn(b"Latest activity", response.data)
        self.assertIn(b"Earlier activity", response.data)
        self.assertIn(b"New log entry", response.data)
        self.assertIn(b"Mark attendance", response.data)
        self.assertIn(b"Submit weekly report", response.data)

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
