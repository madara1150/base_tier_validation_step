from odoo import fields, models


class TierDefinition(models.Model):
    _inherit = "tier.definition"

    need_validated_by_field = fields.Boolean(
        string="Validated by Field",
        help="The reviewer of this tier must press Confirm before the "
        "Validate button becomes available.",
    )
