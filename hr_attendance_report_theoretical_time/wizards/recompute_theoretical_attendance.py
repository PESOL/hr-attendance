# Copyright 2019 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class RecomputeTheoreticalAttendance(models.TransientModel):
    _name = "recompute.theoretical.attendance"
    _description = "Recompute Employees Attendances"

    employee_ids = fields.Many2many(
        comodel_name="hr.employee",
        required=False,
        string="Employees",
        help="Recompute these employees attendances",
    )
    date_from = fields.Datetime(
        string="From", required=True, help="Recompute attendances from this date"
    )
    date_to = fields.Datetime(
        string="To", required=True, help="Recompute attendances up to this date"
    )

    def action_recompute(self):
        self.ensure_one()
        self.env["hr.attendance"]._update_theoretical_attendance(
            self.date_from, self.date_to, employee_ids= self.employee_ids)
        return {"type": "ir.actions.act_window_close"}
