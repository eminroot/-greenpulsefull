import unittest

import numpy as np

from src.decision_explainability import (
    STANDARD_REASON_CODES,
    build_decision_explanation,
    calculate_fusion_contributions,
)

from src.feature_fusion import (
    FUSION_FEATURE_NAMES,
)

from src.multimodal_fusion_model import (
    MultimodalFusionModel,
)


def model():

    weights = [
        0.0
        for _ in FUSION_FEATURE_NAMES
    ]

    weights[0] = 1.0
    weights[31] = -2.0
    weights[49] = 0.5

    scales = [
        1.0
        for _ in FUSION_FEATURE_NAMES
    ]

    scales[31] = 2.0
    scales[49] = 4.0

    return MultimodalFusionModel(
        feature_names=
            list(
                FUSION_FEATURE_NAMES
            ),

        scaler_mean=[
            0.0
            for _ in FUSION_FEATURE_NAMES
        ],

        scaler_scale=
            scales,

        weights=
            weights,

        bias=
            0.1,

        decision_threshold=
            0.5,

        training_iterations=
            1,

        learning_rate=
            0.01,

        l2_strength=
            0.01,
    )


def fused():

    values = [
        0.0
        for _ in FUSION_FEATURE_NAMES
    ]

    values[0] = 2.0
    values[31] = 1.0
    values[49] = 4.0

    return {
        "feature_vector_version":
            "multimodal_feature_vector_v1",

        "feature_vector": {
            "names":
                list(
                    FUSION_FEATURE_NAMES
                ),

            "values":
                values,
        },
    }


def decision():

    return {
        "decision":
            "RECHECK",

        "reason_codes": [
            "MODEL_UNCERTAIN",
            "VISION_SENSOR_CONFLICT",
        ],
    }


class TestDecisionExplainability(
    unittest.TestCase
):

    def test_standard_reason_code_contract(self):

        self.assertEqual(
            STANDARD_REASON_CODES,
            (
                "VISUAL_STRESS_HIGH",
                "VISUAL_DELTA_HIGH",
                "LOW_SOIL_MOISTURE",
                "HIGH_TEMPERATURE",
                "RISK_TREND_RISING",
                "FORECAST_RISK_RISING",
                "TEMPORAL_CONFIRMATION",
                "LOW_CONFIDENCE",
                "IMAGE_QUALITY_LOW",
                "SENSOR_DATA_INVALID",
                "VISION_SENSOR_CONFLICT",
            ),
        )


    def test_reason_order_is_deterministic(self):

        result = build_decision_explanation(
            decision_result=
                decision(),

            reason_flags={
                "VISION_SENSOR_CONFLICT":
                    True,

                "LOW_CONFIDENCE":
                    True,

                "VISUAL_STRESS_HIGH":
                    True,
            },
        )

        self.assertEqual(
            result[
                "standard_reason_codes"
            ],
            [
                "VISUAL_STRESS_HIGH",
                "LOW_CONFIDENCE",
                "VISION_SENSOR_CONFLICT",
            ],
        )


    def test_human_readable_explanation_is_deterministic(self):

        first = build_decision_explanation(
            decision_result=
                decision(),

            reason_flags={
                "LOW_CONFIDENCE":
                    True,
            },
        )

        second = build_decision_explanation(
            decision_result=
                decision(),

            reason_flags={
                "LOW_CONFIDENCE":
                    True,
            },
        )

        self.assertEqual(
            first[
                "human_readable_explanation"
            ],
            second[
                "human_readable_explanation"
            ],
        )


    def test_llm_is_not_used(self):

        result = build_decision_explanation(
            decision_result=
                decision(),

            reason_flags={},
        )

        self.assertFalse(
            result[
                "explanation_generation"
            ][
                "llm_used"
            ]
        )


    def test_unknown_reason_code_rejected(self):

        with self.assertRaises(
            ValueError
        ):

            build_decision_explanation(
                decision_result=
                    decision(),

                reason_flags={
                    "UNDEFINED_REASON":
                        True,
                },
            )


    def test_non_boolean_reason_flag_rejected(self):

        with self.assertRaises(
            ValueError
        ):

            build_decision_explanation(
                decision_result=
                    decision(),

                reason_flags={
                    "LOW_CONFIDENCE":
                        1,
                },
            )


    def test_internal_reason_codes_are_preserved(self):

        result = build_decision_explanation(
            decision_result=
                decision(),

            reason_flags={
                "VISION_SENSOR_CONFLICT":
                    True,
            },
        )

        self.assertEqual(
            result[
                "decision_internal_reason_codes"
            ],
            [
                "MODEL_UNCERTAIN",
                "VISION_SENSOR_CONFLICT",
            ],
        )


    def test_no_model_does_not_invent_feature_importance(self):

        result = build_decision_explanation(
            decision_result=
                decision(),

            reason_flags={},
        )

        self.assertEqual(
            result[
                "fusion_explainability"
            ][
                "status"
            ],
            "NOT_AVAILABLE",
        )


    def test_model_and_features_must_be_supplied_together(self):

        with self.assertRaises(
            ValueError
        ):

            build_decision_explanation(
                decision_result=
                    decision(),

                reason_flags={},

                fusion_model=
                    model(),
            )


    def test_exact_logit_contribution_reconstruction(self):

        result = calculate_fusion_contributions(
            fusion_model=
                model(),

            fused_features=
                fused(),

            top_k=5,
        )

        self.assertTrue(
            result[
                "probability_reconstruction_match"
            ]
        )

        self.assertLessEqual(
            result[
                "probability_reconstruction_error"
            ],
            1e-12,
        )


    def test_contribution_method_is_model_specific_not_causal(self):

        result = calculate_fusion_contributions(
            fusion_model=
                model(),

            fused_features=
                fused(),
        )

        self.assertFalse(
            result[
                "interpretation"
            ][
                "causal_importance"
            ]
        )

        self.assertFalse(
            result[
                "interpretation"
            ][
                "global_feature_importance"
            ]
        )


    def test_modality_contributions_are_available(self):

        result = calculate_fusion_contributions(
            fusion_model=
                model(),

            fused_features=
                fused(),
        )

        modalities = result[
            "modality_logit_contributions"
        ]

        self.assertEqual(
            set(
                modalities
            ),
            {
                "vision",
                "sensor",
                "temporal",
            },
        )


    def test_feature_schema_mismatch_is_blocked(self):

        bad = model()

        bad.feature_names = list(
            reversed(
                bad.feature_names
            )
        )

        with self.assertRaises(
            ValueError
        ):

            calculate_fusion_contributions(
                fusion_model=
                    bad,

                fused_features=
                    fused(),
            )


    def test_top_k_is_respected(self):

        result = calculate_fusion_contributions(
            fusion_model=
                model(),

            fused_features=
                fused(),

            top_k=3,
        )

        self.assertEqual(
            len(
                result[
                    "top_feature_contributions"
                ]
            ),
            3,
        )


    def test_layer_never_authorizes_physical_action(self):

        result = build_decision_explanation(
            decision_result=
                decision(),

            reason_flags={
                "VISION_SENSOR_CONFLICT":
                    True,
            },

            fusion_model=
                model(),

            fused_features=
                fused(),
        )

        self.assertFalse(
            result[
                "scientific_guardrails"
            ][
                "physical_action_authorized"
            ]
        )

        self.assertFalse(
            result[
                "fusion_explainability"
            ][
                "scientific_guardrails"
            ][
                "physical_action_authorized"
            ]
        )


if __name__ == "__main__":
    unittest.main()