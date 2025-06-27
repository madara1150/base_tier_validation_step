
from odoo import _, api, fields, models


class TierValidation(models.AbstractModel):
    _inherit = 'tier.validation'

    validated_by_field = fields.Boolean(
        compute="_compute_validated_by_field",
        string="Validated by Field",
    )

    validated_field = fields.Boolean(
        compute="_compute_validated_field",
        string="Review Validated"
        ,store=True
    )

    @api.model
    def _get_under_validation_exceptions(self):
        exceptions = super()._get_under_validation_exceptions()
        exceptions.append('validated_field')
        return exceptions

    def confirm_by_field(self):
        self.ensure_one()
        self.validated_field = True
        return True

    @api.depends('review_ids.status', 'review_ids.need_validate_field', 'review_ids.sequence')
    def _compute_validated_by_field(self):
        for rec in self:
            review = rec.review_ids.filtered(lambda l: l.status == "pending").sorted(
                key=lambda l: l.sequence
            )
            review = review[0] if review else False
            rec.validated_by_field = review.need_validate_field if review else False

    @api.depends('validated_by_field')
    def _compute_validated_field(self):
        for rec in self:
            review = rec.review_ids.filtered(lambda l: l.status == "pending").sorted(
                key=lambda l: l.sequence
            )
            review = review[0] if review else False
            rec.validated_field = not review.need_validate_field if review else False

    def step_tier_validation(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Step Back Validation',
            'res_model': 'tier.validation.step.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_validation_id': self.id,
                'default_res_model': self._name,
            },
        }
