
from odoo import _, api, fields, models


class TierValidationStepWizard(models.TransientModel):
    _name = 'tier.validation.step.wizard'
    _description = _('TierValidationStepWizard')


    res_model = fields.Char(string="Model", required=True)
    selected_review_id = fields.Many2one(
        comodel_name='tier.review',
        string='Step Back To',
        required=True,
    )
    review_ids = fields.Many2many(
        comodel_name='tier.review',
        string='Validations',
        compute='_compute_review_ids',
        store=False,
    )

    @api.depends('res_model')
    def _compute_review_ids(self):
        for rec in self:
            rec.review_ids = self.env["tier.review"].search([
                ("model", "=", self.res_model),
            ])

    @api.onchange('res_model')
    def _onchange_res_model(self):
        return {
            'domain': {
                'selected_review_id': [('model', '=', self.res_model),
                                       ('status', '=', 'approved')],
            }
        }

    def action_confirm_stepback(self):
        for wizard in self:
            reviews_to_reset = self.review_ids.filtered(
                    lambda r: r.sequence >= wizard.selected_review_id.sequence and r.status == "approved"
                )
            reviews_to_reset.write({
                    "status": "pending",
                    "done_by": False,
                    "reviewed_date": False,
                })
