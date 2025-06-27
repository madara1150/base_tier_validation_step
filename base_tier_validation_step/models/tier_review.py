# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class TierReview(models.Model):
    _inherit = 'tier.review'

    need_validate_field = fields.Boolean(
        string="Need Validate Field", related="definition_id.need_validated_by_field", store=True
    )

