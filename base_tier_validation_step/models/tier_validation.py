from odoo import _, api, fields, models
from odoo.exceptions import AccessError, UserError


class TierValidation(models.AbstractModel):
    _inherit = "tier.validation"

    validated_by_field = fields.Boolean(
        compute="_compute_validated_field",
        string="Validated by Field",
        help="The current user must confirm before validating.",
    )
    validated_field = fields.Boolean(
        compute="_compute_validated_field",
        string="Review Validated",
        help="There is a pending review and nothing left to confirm "
        "for the current user.",
    )
    can_step_back = fields.Boolean(compute="_compute_can_step_back")

    @api.depends_context("uid")
    @api.depends(
        "review_ids.status",
        "review_ids.need_validate_field",
        "review_ids.field_confirmed",
        "review_ids.sequence",
    )
    def _compute_validated_field(self):
        for rec in self:
            needs_confirmation = bool(rec._get_reviews_to_confirm())
            has_pending = "pending" in rec.review_ids.mapped("status")
            rec.validated_by_field = needs_confirmation
            rec.validated_field = has_pending and not needs_confirmation

    @api.depends_context("uid")
    @api.depends("review_ids.status", "review_ids.done_by")
    def _compute_can_step_back(self):
        for rec in self:
            rec.can_step_back = (
                bool(rec._get_step_back_reviews()) and rec._user_can_step_back()
            )

    def _get_reviews_to_confirm(self):
        """Reviews the current user can act on now but must confirm first."""
        self.ensure_one()
        sequences = self._get_sequences_to_approve(self.env.user)
        return self.review_ids.filtered(
            lambda r: r.status == "pending"
            and r.sequence in sequences
            and r.need_validate_field
            and not r.field_confirmed
        )

    def _get_step_back_reviews(self):
        """Reviews the document can step back to."""
        self.ensure_one()
        if not self._check_state_from_condition():
            return self.env["tier.review"]
        return self.review_ids.filtered(
            lambda r: r.status in ("approved", "rejected")
        ).sorted("sequence")

    def _user_can_step_back(self):
        """Allowed to the reviewer whose turn it is, to whoever already reviewed
        the document, and to the members of the step back group."""
        self.ensure_one()
        user = self.env.user
        return (
            self.can_review
            or user in self.review_ids.done_by
            or user.has_group("base_tier_validation_step.group_tier_step_back_manager")
        )

    def _validate_tier(self, tiers=False):
        self.ensure_one()
        reviews = (tiers or self.review_ids).filtered(
            lambda r: r.status == "pending"
            and self.env.user in r.reviewer_ids
            and r.need_validate_field
            and not r.field_confirmed
        )
        if reviews:
            raise UserError(
                _("Please confirm the following tiers before validating:\n- %s")
                % "\n- ".join(reviews.mapped("name"))
            )
        return super()._validate_tier(tiers)

    def confirm_by_field(self):
        self.ensure_one()
        reviews = self._get_reviews_to_confirm()
        if not reviews:
            raise UserError(_("There is nothing for you to confirm on this document."))
        reviews.write(
            {
                "field_confirmed": True,
                "field_confirmed_by": self.env.user.id,
                "field_confirmed_date": fields.Datetime.now(),
            }
        )
        if hasattr(self, "message_post"):
            self.sudo().message_post(
                body=_(
                    "%(user)s confirmed the tier: %(tiers)s",
                    user=self.env.user.name,
                    tiers=", ".join(reviews.mapped("name")),
                )
            )
        return True

    def step_tier_validation(self):
        self.ensure_one()
        self._check_can_step_back()
        return {
            "type": "ir.actions.act_window",
            "name": _("Step Back Validation"),
            "res_model": "tier.validation.step.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_res_model": self._name,
                "default_res_id": self.id,
                "default_selected_review_id": self._get_step_back_reviews()[-1].id,
            },
        }

    def _check_can_step_back(self):
        self.ensure_one()
        if not self._get_step_back_reviews():
            raise UserError(_("This document has no review to step back to."))
        if not self._user_can_step_back():
            raise AccessError(_("You are not allowed to step back this document."))

    def _step_back_to(self, review, reason):
        """Reopen `review` and every later tier."""
        self.ensure_one()
        self._check_can_step_back()
        if review not in self._get_step_back_reviews():
            raise UserError(_("You can only step back to a tier already reviewed."))
        reviews = self.review_ids.filtered(lambda r: r.sequence >= review.sequence)
        reviews.write(reviews._prepare_step_back_vals())
        self._update_counter({"review_created": True})
        self._notify_step_back(review, reviews, reason)

    def _notify_step_back_body(self, review, reason):
        return _(
            "%(user)s stepped the validation back to %(tier)s. Reason: %(reason)s",
            user=self.env.user.name,
            tier=review.name,
            reason=reason,
        )

    def _notify_step_back(self, review, reviews, reason):
        if not hasattr(self, "message_post"):
            return
        subtype_xmlid = self._get_restarted_notification_subtype()
        partners = reviews.filtered(
            lambda r: r.definition_id.notify_on_restarted
        ).reviewer_ids.partner_id
        if partners:
            self.message_subscribe(
                partner_ids=partners.ids,
                subtype_ids=self.env.ref(subtype_xmlid).ids,
            )
        self.sudo().message_post(
            subtype_xmlid=subtype_xmlid,
            body=self._notify_step_back_body(review, reason),
        )
