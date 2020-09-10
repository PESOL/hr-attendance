# Copyright 2017-2019 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, time

import pytz
from psycopg2.extensions import AsIs

from odoo import api, fields, models, tools


class HrAttendanceTheoreticalTimeReport(models.Model):
    _name = "hr.attendance.theoretical.time.report"
    _description = "Report of theoretical time vs attendance time"
    _auto = False
    _rec_name = "date"
    _order = "date,employee_id,theoretical_hours desc"

    employee_id = fields.Many2one(
        comodel_name="hr.employee", string="Employee", readonly=True
    )
    date = fields.Date(string="Date", readonly=True)
    worked_hours = fields.Float(string="Worked", readonly=True)
    theoretical_hours = fields.Float(string="Theoric", readonly=True)
    difference = fields.Float(readonly=True)

    def _select(self):
        # We put "max" aggregation function for theoretical hours because
        # we will recompute for other detail levels different than day
        # through recursivity by day results and will aggregate them manually
        return """
            min(id) AS id,
            employee_id,
            check_in::date AS date,
            sum(worked_hours) AS worked_hours,
            sum(theoretical_hours) AS theoretical_hours,
            sum(theoretical_hours-worked_hours) AS difference
            """

    def _from(self):
        return """
            hr_attendance ha
            """

    def _group_by(self):
        return """
            employee_id,
            check_in
            """

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(
            """
CREATE or REPLACE VIEW %s as (
    SELECT %s
    FROM %s
    GROUP BY %s
)
            """,
            (
                AsIs(self._table),
                AsIs(self._select()),
                AsIs(self._from()),
                AsIs(self._group_by()),
            ),
        )

    # TODO: create cron to execute al days with all employees
    @api.model
    def _theoretical_hours(self, employee, date):
        """Get theoretical working hours for the day where the check-in is
        done for that employee.
        """
        if not employee.resource_id.calendar_id:
            return 0
        tz = employee.resource_id.calendar_id.tz
        return employee.with_context(
            exclude_public_holidays=True, employee_id=employee.id
        )._get_work_days_data(
            datetime.combine(date, time(0, 0, 0, 0, tzinfo=pytz.timezone(tz))),
            datetime.combine(date, time(23, 59, 59, 99999, tzinfo=pytz.timezone(tz))),
            # Pass this domain for excluding leaves whose type is included in
            # theoretical hours
            domain=[
                "|",
                ("holiday_id", "=", False),
                ("holiday_id.holiday_status_id.include_in_theoretical", "=", False),
            ],
        )[
            "hours"
        ]
