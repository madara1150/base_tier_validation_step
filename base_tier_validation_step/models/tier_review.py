from odoo import fields, models


class TierReview(models.Model):
    _inherit = "tier.review"

    need_validate_field = fields.Boolean(
        string="Need Validate Field",
        related="definition_id.need_validated_by_field",
        store=True,
    )
    field_confirmed = fields.Boolean(
        string="Field Confirmed",
        readonly=True,
        copy=False,
    )
    field_confirmed_by = fields.Many2one(
        comodel_name="res.users",
        string="Field Confirmed By",
        readonly=True,
        copy=False,
    )
    field_confirmed_date = fields.Datetime(
        string="Field Confirmed On",
        readonly=True,
        copy=False,
    )

    def _prepare_step_back_vals(self):
        """Values that bring a review back to its initial state."""
        return {
            "status": "pending",
            "done_by": False,
            "reviewed_date": False,
            "comment": False,
            "last_reminder_date": False,
            "field_confirmed": False,
            "field_confirmed_by": False,
            "field_confirmed_date": False,
        }
