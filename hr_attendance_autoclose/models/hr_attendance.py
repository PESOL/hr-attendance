# Copyright 2018 ForgeFlow, S.L.
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from datetime import datetime, timedelta

from odoo import api, fields, models


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    @api.depends("check_out", "check_in")
    def _compute_open_worked_hours(self):
        for attendance in self:
            if attendance.check_out:
                delta = attendance.check_out - attendance.check_in
                open_worked_hours = delta.total_seconds() / 3600.0
            else:
                delta = datetime.now() - attendance.check_in
                open_worked_hours = delta.total_seconds() / 3600.0
            attendance.open_worked_hours = open_worked_hours
        return True

    open_worked_hours = fields.Float(
        string="Worked hours", compute="_compute_open_worked_hours",
    )

    def get_done_hours_same_day(self):
        today = fields.Datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        attendances = self.search(
            [
                ("employee_id", "=", self.employee_id.id),
                ("check_in", ">=", today),
                ("check_out", "!=", False),
            ]
        )
        return sum(attendances.mapped("worked_hours")) if attendances else 0.0

    def autoclose_attendance(self, reason):
        self.ensure_one()
        done_hours = self.get_done_hours_same_day()
        max_hours = (
            self.employee_id.company_id.attendance_maximum_hours_per_day - done_hours
        )
        leave_time = self.check_in + timedelta(hours=max_hours)
        vals = {"check_out": leave_time}
        if reason:
            vals["attendance_reason_ids"] = [(4, reason.id)]
        self.write(vals)

    def needs_autoclose(self):
        self.ensure_one()
        max_hours = self.employee_id.company_id.attendance_maximum_hours_per_day
        close = not self.employee_id.no_autoclose
        done_hours = self.get_done_hours_same_day()
        return close and max_hours and self.open_worked_hours + done_hours > max_hours

    @api.model
    def check_for_incomplete_attendances(self):
        stale_attendances = self.search([("check_out", "=", False)])
        reason = self.env["hr.attendance.reason"].search(
            [("code", "=", "S-CO")], limit=1
        )
        for att in stale_attendances.filtered(lambda a: a.needs_autoclose()):
            att.autoclose_attendance(reason)

    @api.constrains("check_in", "check_out", "employee_id")
    def _check_validity(self):
        """ If this is an automatic checkout the constraint is invalid
        as there may be old attendances not closed
        """
        reason = self.env["hr.attendance.reason"].search(
            [("code", "=", "S-CO")], limit=1
        )
        if not reason:
            return super(HrAttendance, self)._check_validity()
        if self.filtered(
            lambda att: att.attendance_reason_ids
            and reason in att.attendance_reason_ids
        ):
            return True
        return super(HrAttendance, self)._check_validity()
