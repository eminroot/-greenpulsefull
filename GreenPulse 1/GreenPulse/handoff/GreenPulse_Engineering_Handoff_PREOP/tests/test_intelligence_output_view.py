import copy
import unittest

from src.intelligence_output_view import (
    BACKEND_FIELDS,
    FRONTEND_WIDGETS,
    SCHEMA_VERSION,
    build_intelligence_output_view,
)


def full_observation():

    return {
        "plant_state":
            "MONITORING",

        "confidence":
            0.91,

        "risk_score":
            37.0,

        "trend":
            "STABLE",

        "forecast": {
            "risk":
                40.0,

            "horizon_minutes":
                30,
        },

        "sensors": {
            "soil_moisture":
                42.0,

            "temperature":
                25.0,
        },

        "uncertainty": {
            "status":
                "LOW"
        },

        "decision":
            "MONITOR",

        "reasons": [
            "REFERENCE_TEST"
        ],

        "model_version":
            "TEST_MODEL_V1",

        "latency":
            {
                "end_to_end_ms":
                    50.0
            },

        "system_status":
            "HEALTHY",
    }


class TestIntelligenceOutputView(
    unittest.TestCase
):

    def test_schema_version(self):

        result = build_intelligence_output_view(
            full_observation()
        )

        self.assertEqual(
            result[
                "schema_version"
            ],
            "greenpulse.intelligence_output_view.v1",
        )


    def test_backend_field_count(self):

        result = build_intelligence_output_view(
            full_observation()
        )

        self.assertEqual(
            set(
                result[
                    "backend"
                ]
            ),
            set(
                BACKEND_FIELDS
            ),
        )


    def test_full_backend_has_no_missing_values(self):

        result = build_intelligence_output_view(
            full_observation()
        )

        self.assertEqual(
            result[
                "availability"
            ][
                "missing_backend_values"
            ],
            [],
        )


    def test_frontend_widget_contract_count(self):

        result = build_intelligence_output_view(
            full_observation()
        )

        self.assertEqual(
            set(
                result[
                    "frontend"
                ]
            ),
            set(
                FRONTEND_WIDGETS
            ),
        )


    def test_risk_gauge_maps_risk(self):

        result = build_intelligence_output_view(
            full_observation()
        )

        self.assertEqual(
            result[
                "frontend"
            ][
                "risk_gauge"
            ][
                "value"
            ],
            37.0,
        )


    def test_decision_explanation_maps_reasons(self):

        result = build_intelligence_output_view(
            full_observation()
        )

        widget = result[
            "frontend"
        ][
            "decision_explanation"
        ]

        self.assertEqual(
            widget[
                "decision"
            ],
            "MONITOR",
        )

        self.assertEqual(
            widget[
                "reasons"
            ],
            [
                "REFERENCE_TEST"
            ],
        )


    def test_system_health_maps_status_uncertainty_latency(self):

        result = build_intelligence_output_view(
            full_observation()
        )

        widget = result[
            "frontend"
        ][
            "system_health"
        ]

        self.assertEqual(
            widget[
                "system_status"
            ],
            "HEALTHY",
        )

        self.assertEqual(
            widget[
                "uncertainty"
            ],
            {
                "status":
                    "LOW"
            },
        )


    def test_missing_plant_state_is_explicit_null(self):

        observation = full_observation()

        observation.pop(
            "plant_state"
        )

        result = build_intelligence_output_view(
            observation
        )

        self.assertIsNone(
            result[
                "backend"
            ][
                "plant_state"
            ]
        )

        self.assertIn(
            "plant_state",
            result[
                "availability"
            ][
                "missing_backend_values"
            ],
        )


    def test_optional_widgets_default_unavailable(self):

        result = build_intelligence_output_view(
            full_observation()
        )

        self.assertFalse(
            result[
                "frontend"
            ][
                "last_action"
            ][
                "available"
            ]
        )

        self.assertFalse(
            result[
                "frontend"
            ][
                "before_after_intervention"
            ][
                "available"
            ]
        )


    def test_optional_widget_payloads_pass_through(self):

        result = build_intelligence_output_view(
            full_observation(),
            image={
                "available":
                    True,

                "image":
                    "fixture://image",
            },
            last_action={
                "available":
                    True,

                "action":
                    "SIMULATED",
            },
            intervention={
                "available":
                    True,

                "before":
                    50,

                "after":
                    30,
            },
            sustainability={
                "available":
                    True,

                "score":
                    42,
            },
        )

        self.assertTrue(
            result[
                "frontend"
            ][
                "live_or_annotated_image"
            ][
                "available"
            ]
        )

        self.assertEqual(
            result[
                "frontend"
            ][
                "sustainability_score"
            ][
                "score"
            ],
            42,
        )


    def test_input_not_mutated(self):

        observation = full_observation()

        original = copy.deepcopy(
            observation
        )

        build_intelligence_output_view(
            observation
        )

        self.assertEqual(
            observation,
            original,
        )


    def test_frontend_rendering_not_claimed(self):

        result = build_intelligence_output_view(
            full_observation()
        )

        self.assertFalse(
            result[
                "claim_boundary"
            ][
                "frontend_rendering_implemented"
            ]
        )

        self.assertTrue(
            result[
                "claim_boundary"
            ][
                "widget_payload_contract_complete"
            ]
        )


    def test_missing_values_never_fabricated(self):

        result = build_intelligence_output_view(
            {}
        )

        self.assertEqual(
            result[
                "availability"
            ][
                "backend_fields_present"
            ],
            0,
        )

        self.assertFalse(
            result[
                "claim_boundary"
            ][
                "missing_values_fabricated"
            ]
        )


if __name__ == "__main__":
    unittest.main()