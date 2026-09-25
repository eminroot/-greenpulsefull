
import copy
import unittest

from src.crop_adaptation_eval import (
    evaluate_adaptation_evidence,
    validate_protocol
)


class CropAdaptationTests(unittest.TestCase):

    def setUp(self):

        self.protocol = {
            "version": "1.0",
            "mode": "RESEARCH_ONLY",
            "required_experiment_arms": [
                "SOURCE_CROP_PRETRAINED",
                "GENERIC_PRETRAINED_BASELINE"
            ],
            "required_controls": {
                "same_target_dataset": True,
                "same_train_validation_split": True,
                "same_random_seed": True,
                "same_image_size": True,
                "same_epoch_budget": True,
                "same_optimizer_family": True,
                "same_learning_rate": True,
                "same_early_stopping_policy": True
            },
            "future_adaptation_training": {
                "freeze_strategy_must_be_declared_before_training": True,
                "selected_backbone_freeze_required_for_protocol_arm": True,
                "freeze_configuration_must_be_recorded": True
            },
            "model_selection_split": "VALIDATION",
            "held_out_test_policy": {
                "use_for_model_selection": False,
                "use_for_threshold_tuning": False,
                "single_final_evaluation_only": True
            },
            "minimum_reported_metrics": [],
            "transfer_advantage_policy": {
                "validation_difference_required": True,
                "do_not_claim_advantage_when_metrics_tie": True,
                "causal_advantage_claim_allowed": False
            },
            "real_greenhouse_generalization_required_for_operational_claim": True,
            "physical_actuation_allowed": False
        }

        self.transfer = {
            "training_completed": True,
            "best_checkpoint_sha256":
                "a" * 64
        }

        self.baseline = {
            "training_completed": True,
            "best_checkpoint_sha256":
                "b" * 64
        }

        metrics = {
            "accuracy": 1.0,
            "balanced_accuracy": 1.0,
            "macro_precision": 1.0,
            "macro_recall": 1.0,
            "macro_f1": 1.0
        }

        self.comparison = {
            "comparison_split":
                "VALIDATION_ONLY",
            "test_images_evaluated": 0,
            "transfer_checkpoint_sha256":
                "a" * 64,
            "baseline_checkpoint_sha256":
                "b" * 64,
            "validation_images": 371,
            "validation_leaf_groups": 51,
            "transfer_metrics":
                copy.deepcopy(metrics),
            "baseline_metrics":
                copy.deepcopy(metrics),
            "observed_macro_f1_difference":
                0.0,
            "paired_results": {
                "both_correct": 371,
                "transfer_only_correct": 0,
                "baseline_only_correct": 0,
                "both_wrong": 0
            }
        }

        self.final = {
            "evaluation_split":
                "FROZEN_FINAL_TEST",
            "checkpoint_sha256":
                "a" * 64,
            "test_used_for_model_selection":
                False,
            "metrics": {
                "accuracy": 0.9811,
                "macro_f1": 0.9802
            },
            "error_analysis": {
                "total_errors": 7
            }
        }

    def evaluate(self):

        return evaluate_adaptation_evidence(
            self.transfer,
            self.baseline,
            self.comparison,
            self.final,
            self.protocol
        )

    def test_01_protocol_valid(self):

        self.assertTrue(
            validate_protocol(
                self.protocol
            )
        )

    def test_02_tied_models_no_advantage(self):

        result = self.evaluate()

        self.assertTrue(
            result[
                "validation_metrics_tied"
            ]
        )

        self.assertFalse(
            result[
                "transfer_advantage_observed"
            ]
        )

        self.assertFalse(
            result[
                "causal_transfer_advantage_established"
            ]
        )

    def test_03_missing_freeze_not_hidden(self):

        result = self.evaluate()

        self.assertFalse(
            result[
                "selected_backbone_freeze_documented"
            ]
        )

        self.assertFalse(
            result[
                "frozen_backbone_protocol_fully_satisfied"
            ]
        )

    def test_04_documented_freeze_detected(self):

        self.transfer[
            "freeze_strategy"
        ] = {
            "frozen_layers": [
                0, 1, 2
            ]
        }

        result = self.evaluate()

        self.assertTrue(
            result[
                "selected_backbone_freeze_documented"
            ]
        )

    def test_05_test_contamination_rejected(self):

        self.comparison[
            "test_images_evaluated"
        ] = 371

        with self.assertRaisesRegex(
            ValueError,
            "TEST_CONTAMINATED"
        ):
            self.evaluate()

    def test_06_test_model_selection_rejected(self):

        self.final[
            "test_used_for_model_selection"
        ] = True

        with self.assertRaisesRegex(
            ValueError,
            "TEST_USED_FOR_MODEL_SELECTION"
        ):
            self.evaluate()

    def test_07_checkpoint_mismatch_rejected(self):

        self.final[
            "checkpoint_sha256"
        ] = "c" * 64

        with self.assertRaisesRegex(
            ValueError,
            "FINAL_TEST_CHECKPOINT_MISMATCH"
        ):
            self.evaluate()

    def test_08_unsafe_protocol_rejected(self):

        self.protocol[
            "physical_actuation_allowed"
        ] = True

        with self.assertRaisesRegex(
            ValueError,
            "ACTUATION_MUST_BE_DISABLED"
        ):
            self.evaluate()


if __name__ == "__main__":
    unittest.main()
