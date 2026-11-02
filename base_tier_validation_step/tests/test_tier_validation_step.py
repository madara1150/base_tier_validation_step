from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, tagged

from odoo.addons.base_tier_validation.tests.common import CommonTierValidation


@tagged("post_install", "-at_install")
class TestTierValidationStep(CommonTierValidation):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_user_3 = cls.test_user_3_multi_company
        # The common setup defines a tier for test_field > 1: use another value
        # range so that only the tiers below apply.
        cls.tier_definition.definition_domain = "[('test_field', '=', -1)]"
        cls.tier_1 = cls._create_tier("Manager", 30, cls.test_user_1)
        cls.tier_2 = cls._create_tier("Finance", 20, cls.test_user_2)
        cls.tier_3 = cls._create_tier("Director", 10, cls.test_user_3)
        cls.record = cls._create_record()

    @classmethod
    def _create_tier(cls, name, sequence, reviewer, **vals):
        return cls.tier_def_obj.create(
            dict(
                {
                    "name": name,
                    "model_id": cls.tester_model.id,
                    "review_type": "individual",
                    "reviewer_id": reviewer.id,
                    "definition_domain": "[('test_field', '=', 5)]",
                    "approve_sequence": True,
                    "notify_on_restarted": True,
                    "sequence": sequence,
                },
                **vals,
            )
        )

    @classmethod
    def _create_record(cls):
        record = cls.test_model.create({"test_field": 5})
        record.with_user(cls.test_user_2).request_validation()
        return record

    def _review(self, tier, record=None):
        return (record or self.record).review_ids.filtered(
            lambda r: r.definition_id == tier
        )

    def _validate(self, user, record=None):
        (record or self.record).invalidate_recordset()
        (record or self.record).with_user(user).validate_tier()

    def _step_back(self, user, tier, record=None, reason="Wrong amount"):
        record = record or self.record
        record.invalidate_recordset()
        action = record.with_user(user).step_tier_validation()
        wizard_form = Form(
            self.env[action["res_model"]]
            .with_user(user)
            .with_context(**action["context"]),
        )
        wizard_form.selected_review_id = self._review(tier, record)
        wizard_form.reason = reason
        wizard_form.save().action_confirm_stepback()
        record.invalidate_recordset()

    # Confirmation before validating

    def test_field_gate_blocks_validate(self):
        self.tier_1.need_validated_by_field = True
        record = self.record.with_user(self.test_user_1)
        self.assertTrue(record.validated_by_field)
        self.assertFalse(record.validated_field)
        with self.assertRaisesRegex(UserError, "Please confirm"):
            record.validate_tier()
        self.assertEqual(self._review(self.tier_1).status, "pending")

    def test_confirm_then_validate(self):
        self.tier_1.need_validated_by_field = True
        record = self.record.with_user(self.test_user_1)
        self.assertTrue(record.confirm_by_field())
        review = self._review(self.tier_1)
        self.assertTrue(review.field_confirmed)
        self.assertEqual(review.field_confirmed_by, self.test_user_1)
        self.assertTrue(review.field_confirmed_date)
        record.invalidate_recordset()
        self.assertFalse(record.validated_by_field)
        self.assertTrue(record.validated_field)
        self._validate(self.test_user_1)
        self.assertEqual(review.status, "approved")

    def test_tier_without_gate_is_validated_directly(self):
        record = self.record.with_user(self.test_user_1)
        self.assertFalse(record.validated_by_field)
        self.assertTrue(record.validated_field)
        with self.assertRaisesRegex(UserError, "nothing for you to confirm"):
            record.confirm_by_field()
        self._validate(self.test_user_1)
        self.assertEqual(self._review(self.tier_1).status, "approved")

    def test_only_current_reviewer_can_confirm(self):
        self.tier_1.need_validated_by_field = True
        record = self.record.with_user(self.test_user_2)
        self.assertFalse(record.validated_by_field)
        with self.assertRaises(UserError):
            record.confirm_by_field()
        self.assertFalse(self._review(self.tier_1).field_confirmed)

    def test_confirmation_survives_other_review(self):
        (self.tier_1 | self.tier_2).approve_sequence = False
        self.tier_2.need_validated_by_field = True
        self.record.with_user(self.test_user_2).confirm_by_field()
        self._validate(self.test_user_1)
        record = self.record.with_user(self.test_user_2)
        record.invalidate_recordset()
        self.assertTrue(record.validated_field)
        self._validate(self.test_user_2)
        self.assertEqual(self._review(self.tier_2).status, "approved")

    def test_next_gated_tier_needs_its_own_confirmation(self):
        (self.tier_1 | self.tier_2).need_validated_by_field = True
        self.record.with_user(self.test_user_1).confirm_by_field()
        self._validate(self.test_user_1)
        record = self.record.with_user(self.test_user_2)
        record.invalidate_recordset()
        self.assertTrue(record.validated_by_field)
        self.assertFalse(record.validated_field)

    def test_gate_also_applies_to_comment_wizard(self):
        self.tier_1.write({"need_validated_by_field": True, "has_comment": True})
        record = self.record.with_user(self.test_user_1)
        action = record.validate_tier()
        wizard = (
            self.env["comment.wizard"]
            .with_user(self.test_user_1)
            .with_context(action["context"])
            .create({"comment": "ok"})
        )
        with self.assertRaisesRegex(UserError, "Please confirm"):
            wizard.add_comment()

    def test_gate_blocks_auto_validation_on_confirm(self):
        self.tier_1.need_validated_by_field = True
        (self.tier_2 | self.tier_3).active = False
        record = self.test_model.with_user(self.test_user_1).create({"test_field": 5})
        with self.assertRaises(UserError):
            record.action_confirm()
        self.assertEqual(record.state, "draft")

    # Step back

    def test_step_back_reopens_selected_and_later_tiers(self):
        self._validate(self.test_user_1)
        self._validate(self.test_user_2)
        self._review(self.tier_1).comment = "Looks fine"
        self._step_back(self.test_user_3, self.tier_1)
        for tier in self.tier_1 | self.tier_2:
            review = self._review(tier)
            self.assertEqual(review.status, "pending")
            self.assertFalse(review.done_by)
            self.assertFalse(review.reviewed_date)
            self.assertFalse(review.comment)
        self.assertEqual(self.record.validation_status, "pending")

    def test_step_back_keeps_earlier_tiers(self):
        self._validate(self.test_user_1)
        self._validate(self.test_user_2)
        self._step_back(self.test_user_3, self.tier_2)
        self.assertEqual(self._review(self.tier_1).status, "approved")
        self.assertEqual(self._review(self.tier_1).done_by, self.test_user_1)
        self.assertEqual(self._review(self.tier_2).status, "pending")

    def test_step_back_does_not_touch_other_documents(self):
        other = self._create_record()
        self._validate(self.test_user_1)
        self._validate(self.test_user_1, other)
        self._step_back(self.test_user_2, self.tier_1)
        self.assertEqual(self._review(self.tier_1).status, "pending")
        self.assertEqual(self._review(self.tier_1, other).status, "approved")

    def test_step_back_refuses_review_of_other_document(self):
        other = self._create_record()
        self._validate(self.test_user_1)
        self._validate(self.test_user_1, other)
        wizard = (
            self.env["tier.validation.step.wizard"]
            .with_user(self.test_user_2)
            .create(
                {
                    "res_model": self.record._name,
                    "res_id": self.record.id,
                    "selected_review_id": self._review(self.tier_1, other).id,
                    "reason": "Tampered",
                }
            )
        )
        with self.assertRaisesRegex(UserError, "already reviewed"):
            wizard.action_confirm_stepback()
        self.assertEqual(self._review(self.tier_1, other).status, "approved")

    def test_step_back_gives_the_turn_back(self):
        self._validate(self.test_user_1)
        self._step_back(self.test_user_2, self.tier_1)
        review_2 = self._review(self.tier_2)
        self.assertFalse(review_2.can_review)
        self.assertTrue(self._review(self.tier_1).can_review)
        self._validate(self.test_user_1)
        self._validate(self.test_user_2)
        self.assertEqual(review_2.status, "approved")

    def test_step_back_clears_confirmation(self):
        self.tier_1.need_validated_by_field = True
        self.record.with_user(self.test_user_1).confirm_by_field()
        self._validate(self.test_user_1)
        self._step_back(self.test_user_2, self.tier_1)
        review = self._review(self.tier_1)
        self.assertFalse(review.field_confirmed)
        self.assertFalse(review.field_confirmed_by)
        self.assertTrue(self.record.with_user(self.test_user_1).validated_by_field)

    def test_step_back_clears_confirmation_of_pending_tier(self):
        self.tier_2.need_validated_by_field = True
        self._validate(self.test_user_1)
        self.record.with_user(self.test_user_2).confirm_by_field()
        self._step_back(self.test_user_2, self.tier_1)
        self.assertFalse(self._review(self.tier_2).field_confirmed)

    def test_step_back_from_validated_document(self):
        self._validate(self.test_user_1)
        self._validate(self.test_user_2)
        self._validate(self.test_user_3)
        self.assertEqual(self.record.validation_status, "validated")
        self._step_back(self.test_user_3, self.tier_3)
        self.assertEqual(self.record.validation_status, "pending")

    def test_step_back_from_rejected_document(self):
        self._validate(self.test_user_1)
        self.record.with_user(self.test_user_2).reject_tier()
        self.assertEqual(self.record.validation_status, "rejected")
        self._step_back(self.test_user_2, self.tier_2)
        self.assertEqual(self.record.validation_status, "pending")
        self.assertEqual(self._review(self.tier_1).status, "approved")

    def test_step_back_refused_after_confirmation(self):
        self._validate(self.test_user_1)
        self._validate(self.test_user_2)
        self._validate(self.test_user_3)
        self.record.action_confirm()
        record = self.record.with_user(self.test_user_1)
        self.assertFalse(record.can_step_back)
        with self.assertRaisesRegex(UserError, "no review to step back"):
            record.step_tier_validation()

    def test_step_back_without_reviewed_tier(self):
        record = self.record.with_user(self.test_user_1)
        self.assertFalse(record.can_step_back)
        with self.assertRaisesRegex(UserError, "no review to step back"):
            record.step_tier_validation()

    def test_step_back_refused_to_outsider(self):
        self._validate(self.test_user_1)
        outsider = self.env["res.users"].create({"name": "Sam", "login": "outsider"})
        record = self.record.with_user(outsider)
        self.assertFalse(record.can_step_back)
        with self.assertRaises(AccessError):
            record.step_tier_validation()

    def test_step_back_refused_to_reviewer_out_of_turn(self):
        self._validate(self.test_user_1)
        record = self.record.with_user(self.test_user_3)
        self.assertFalse(record.can_step_back)

    def test_step_back_allowed_to_group(self):
        self._validate(self.test_user_1)
        group = self.env.ref("base_tier_validation_step.group_tier_step_back_manager")
        self.test_user_3.groups_id += group
        self._step_back(self.test_user_3, self.tier_1)
        self.assertEqual(self._review(self.tier_1).status, "pending")

    def test_step_back_notifies_in_chatter(self):
        self._validate(self.test_user_1)
        self._step_back(self.test_user_2, self.tier_1, reason="Wrong vendor")
        self.assertIn("Wrong vendor", self.record.message_ids[0].body)
        self.assertIn(self.test_user_1.partner_id, self.record.message_partner_ids)

    def test_step_back_on_model_without_chatter(self):
        record = self.test_record_2.with_user(self.test_user_3)
        record.sudo().request_validation()
        self.env["tier.review"].flush_model()
        record.invalidate_recordset()
        record.validate_tier()
        self.assertTrue(record.can_step_back)
        record._step_back_to(record.review_ids.filtered("done_by"), "No chatter")
        self.assertFalse(record.sudo().review_ids.filtered("done_by"))

    def test_wizard_defaults_to_last_reviewed_tier(self):
        self._validate(self.test_user_1)
        self._validate(self.test_user_2)
        record = self.record.with_user(self.test_user_3)
        record.invalidate_recordset()
        action = record.step_tier_validation()
        self.assertEqual(
            action["context"]["default_selected_review_id"],
            self._review(self.tier_2).id,
        )

    def test_wizard_lists_only_reviews_of_the_document(self):
        other = self._create_record()
        self._validate(self.test_user_1)
        self._validate(self.test_user_2)
        self._validate(self.test_user_1, other)
        wizard = self.env["tier.validation.step.wizard"].create(
            {
                "res_model": self.record._name,
                "res_id": self.record.id,
                "selected_review_id": self._review(self.tier_1).id,
                "reason": "Check",
            }
        )
        self.assertEqual(
            wizard.available_review_ids,
            self._review(self.tier_1) | self._review(self.tier_2),
        )
        self.assertEqual(wizard.reset_review_ids, self.record.review_ids)

    # Views

    def test_buttons_are_in_generated_form(self):
        arch = self.test_model_2.get_view(view_type="form")["arch"]
        self.assertIn(b'name="step_tier_validation"', arch)
        self.assertIn(b'name="confirm_by_field"', arch)
