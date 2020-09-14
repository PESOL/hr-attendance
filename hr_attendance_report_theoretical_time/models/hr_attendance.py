# Copyright 2017-2019 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from datetime import date, datetime, timedelta

class ResCompany(models.Model):
    _inherit = "res.company"

    last_theorical_attendance = fields.Datetime(
        string='Last Theorical Attendance',
        default='2020-01-01')


    def cron_theoretical_hours(self):
        for record in self.search([
                ('last_theorical_attendance', '<', fields.Date.today())
            ]):
            self.env['hr.attendance']._update_theoretical_attendance(
                record.last_theorical_attendance,
                record.last_theorical_attendance
            )
            last_date = fields.Date.from_string(
                record.last_theorical_attendance)
            next_date = last_date + timedelta(days=1)
            record.last_theorical_attendance = fields.Date.to_string(next_date)

class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    time_off = fields.Float()
    theoretical_hours = fields.Float()
    type = fields.Selection(
        [('real', 'Real'),
         ('theoretical', 'Theoretical')],
        default='real',
        string='Type')



    def _compute_theoretical_hours(self):
        obj = self.env["hr.attendance.theoretical.time.report"]
        for record in self.filtered(lambda a: a.type == 'theoretical'):
            theoretical_hours = obj._theoretical_hours(
                record.employee_id, record.check_in
            )
            time_off  = obj._compute_leave_hours(
                record.employee_id, record.check_in
            )
            record.write({
                'theoretical_hours': theoretical_hours,
                'time_off': time_off,
            })

    @api.model
    def _update_theoretical_attendance(
            self, from_date, to_date, employee_ids=False):
        time_report_obj = self.env["hr.attendance.theoretical.time.report"]
        from_date = from_date or fields.Datetime.now()
        to_date = to_date or fields.Datetime.now()
        employee_ids = employee_ids or \
            self.env['hr.employee'].search([])
        employees =  employee_ids.filtered(
            lambda e: e.create_date < to_date and (
                not e.theoretical_hours_start_date
                or (e.theoretical_hours_start_date
                and e.theoretical_hours_start_date < to_date)
            )
        )
        for employee in employees:
            start_date = max([
                from_date,
                employee.theoretical_hours_start_date or employee.create_date
                ])
            delta = to_date - start_date
            for i in range(delta.days + 1):
                day = start_date + timedelta(days=i)
                day_datetime = datetime(day.year, day.month, day.day)
                theoretical_hours = time_report_obj._theoretical_hours(
                    employee, day
                )
                time_off  = time_report_obj._compute_leave_hours(
                    employee, day
                )
                if not ( theoretical_hours or time_off):
                    continue
                attendance = self.search([
                    ('employee_id', '=', employee.id),
                    ('type', '=', 'theoretical'),
                    ('check_in', '=', day_datetime),
                    ('check_out', '=', day_datetime)
                ])
                if not attendance:
                    self.create({
                        'employee_id': employee.id,
                        'type': 'theoretical',
                        'check_in': day_datetime,
                        'check_out': day_datetime,
                        'theoretical_hours': theoretical_hours,
                        'time_off': time_off
                    })
                else:
                    attendance.write({
                        'theoretical_hours': theoretical_hours,
                        'time_off': time_off
                    })
