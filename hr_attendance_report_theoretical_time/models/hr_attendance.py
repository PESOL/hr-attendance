# Copyright 2017-2019 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from datetime import date, datetime, timedelta

class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    theoretical_hours = fields.Float(
        compute="_compute_theoretical_hours", store=True, compute_sudo=True
    )
    type = fields.Selection(
        [('real', 'Real'),
         ('theoretical', 'Theoretical')],
        default='real',
        string='Type')


    @api.depends("check_in", "employee_id")
    def _compute_theoretical_hours(self):
        obj = self.env["hr.attendance.theoretical.time.report"]
        for record in self.filtered(lambda a: a.type == 'theoretical'):
            record.theoretical_hours = obj._theoretical_hours(
                record.employee_id, record.check_in
            )

    @api.model
    def _update_theoretical_attendance(
            self, from_date, to_date, employee_ids=False):
        from_date = from_date or fields.Date.today()
        to_date = to_date or fields.Date.today()
        employees = self.env['hr.employee'].browse(employee_ids) or \
            self.env['hr.employee'].search([
                ('create_date', '<', to_date),
                '|',
                ('theoretical_hours_start_date', '=', False),
                ('theoretical_hours_start_date', '<', to_date),
            ])
        for employee in employees:
            start_date = max([
                from_date,
                employee.theoretical_hours_start_date or employee.create_date
                ])
            delta = to_date - start_date
            for i in range(delta.days + 1):
                day = start_date + timedelta(days=i)
                day_datetime = datetime(day.year, day.month, day.day)
                attendance = self.search([
                    ('employee_id', '=', employee.id),
                    ('type', '=', 'theoretical'),
                    ('check_in', '=', day_datetime),
                    ('check_out', '=', day_datetime)
                ])
                attendance = attendance or self.create({
                    'employee_id': employee.id,
                    'type': 'theoretical',
                    'check_in': day_datetime,
                    'check_out': day_datetime
                })
                attendance._compute_theoretical_hours()
