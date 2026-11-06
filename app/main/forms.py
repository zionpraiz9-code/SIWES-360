from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    IntegerField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    Length,
    NumberRange,
    Optional,
    ValidationError,
)


class DailyLogForm(FlaskForm):
    log_date = DateField(
        "Date",
        format="%Y-%m-%d",
        validators=[DataRequired()],
        default=date.today,
    )
    title = StringField(
        "Activity Title",
        validators=[DataRequired(), Length(max=120)],
    )
    activities = TextAreaField(
        "Detailed Description",
        validators=[DataRequired(), Length(max=5000)],
    )
    tools_used = TextAreaField(
        "Tools & Technologies Used",
        validators=[Optional(), Length(max=2000)],
    )
    skills_learned = TextAreaField(
        "Skills Learned",
        validators=[Optional(), Length(max=2000)],
    )
    challenges_encountered = TextAreaField(
        "Challenges Encountered",
        validators=[Optional(), Length(max=3000)],
    )
    submit = SubmitField("Submit Daily Log")

    def validate_log_date(self, field):
        if field.data and field.data > date.today():
            raise ValidationError("The log date cannot be in the future.")


class WeeklyReportForm(FlaskForm):
    week_number = IntegerField(
        "Week number",
        validators=[DataRequired(), NumberRange(min=1, max=53)],
        default=lambda: date.today().isocalendar().week,
    )
    summary = TextAreaField(
        "Summary of activities",
        validators=[DataRequired(), Length(max=10000)],
    )
    challenges_encountered = TextAreaField(
        "Challenges encountered",
        validators=[DataRequired(), Length(max=5000)],
    )
    plans_for_next_week = TextAreaField(
        "Plans for next week",
        validators=[DataRequired(), Length(max=5000)],
    )
    submit = SubmitField("Submit weekly report")

    def validate_week_number(self, field):
        if not field.data:
            return

        today = date.today()
        iso_year = today.isocalendar().year
        current_week = today.isocalendar().week
        last_week_of_year = date(iso_year, 12, 28).isocalendar().week
        if field.data > last_week_of_year:
            raise ValidationError(
                f"Choose a week number between 1 and {last_week_of_year}."
            )
        if field.data > current_week:
            raise ValidationError("You cannot submit a report for a future week.")


class PlacementForm(FlaskForm):
    matric_number = StringField(
        "Matric number",
        validators=[Optional(), Length(max=64)],
    )
    department = StringField(
        "Department",
        validators=[Optional(), Length(max=160)],
    )
    company_name = StringField(
        "Company name",
        validators=[DataRequired(), Length(max=160)],
    )
    company_address = TextAreaField(
        "Company address",
        validators=[DataRequired(), Length(max=2000)],
    )
    supervisor_name = StringField(
        "Supervisor name",
        validators=[DataRequired(), Length(max=120)],
    )
    supervisor_email = StringField(
        "Supervisor email",
        validators=[DataRequired(), Email(), Length(max=255)],
    )
    supervisor_phone = StringField(
        "Supervisor phone",
        validators=[DataRequired(), Length(max=32)],
    )
    start_date = DateField(
        "Placement start date",
        format="%Y-%m-%d",
        validators=[DataRequired()],
    )
    end_date = DateField(
        "Placement end date",
        format="%Y-%m-%d",
        validators=[DataRequired()],
    )
    submit = SubmitField("Save placement details")

    def validate_end_date(self, field):
        if self.start_date.data and field.data and field.data < self.start_date.data:
            raise ValidationError(
                "The placement end date must be on or after the start date."
            )
