# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class TierDefinition(models.Model):
    _inherit = 'tier.definition'

    need_validated_by_field = fields.Boolean(
        default=False, string="Validated by Field",
    )
