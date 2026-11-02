from odoo import api, fields, models


class TierValidationStepWizard(models.TransientModel):
    _name = "tier.validation.step.wizard"
    _description = "Tier Validation Step Back Wizard"

    res_model = fields.Char(string="Model", required=True)
    res_id = fields.Integer(string="Document ID", required=True)
    available_review_ids = fields.Many2many(
        comodel_name="tier.review",
        string="Available Reviews",
        compute="_compute_available_review_ids",
    )
    selected_review_id = fields.Many2one(
        comodel_name="tier.review",
        string="Step Back To",
        required=True,
        domain="[('id', 'in', available_review_ids)]",
    )
    reset_review_ids = fields.Many2many(
        comodel_name="tier.review",
        string="Reviews to Reopen",
        compute="_compute_reset_review_ids",
    )
    reason = fields.Text(required=True)

    def _get_document(self):
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id)

    @api.depends("res_model", "res_id")
    def _compute_available_review_ids(self):
        for wizard in self:
            wizard.available_review_ids = (
                wizard._get_document()._get_step_back_reviews()
            )

    @api.depends("res_model", "res_id", "selected_review_id")
    def _compute_reset_review_ids(self):
        for wizard in self:
            sequence = wizard.selected_review_id.sequence
            wizard.reset_review_ids = (
                wizard._get_document().review_ids.filtered(
                    lambda r: r.sequence >= sequence
                )
                if wizard.selected_review_id
                else False
            )

    def action_confirm_stepback(self):
        self.ensure_one()
        self._get_document()._step_back_to(self.selected_review_id, self.reason)
