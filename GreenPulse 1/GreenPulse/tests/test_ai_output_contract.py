import unittest

from src.ai_output_contract import (
    NULL_FALLBACK_POLICY,
    NULL_POLICY_VERSION,
    SCHEMA_VERSION,
    build_standard_ai_output,
)


def master_payload():

    return {
        "schema_version":
            "greenpulse.master_observation_output.v1",

        "pipeline_version":
            "greenpulse.master_ai_inference_pipeline.v1",

        "observation_id":
            "OBS-MASTER-001",

        "plant_id":
            "P01",

        "crop":
            "tomato",

        "image_captured_at":
            "2026-09-24T10:00:00+00:00",

        "sensor_timestamp":
            "2026-09-24T10:00:01+00:00",

        "stages": {
            "vision_inference": {
                "status":
                    "SUCCESS",

                "vision": {
                    "state":
                        "DISEASE_PATTERN_PREDICTED",

                    "confidence":
                        0.91,
                },

                "model": {
                    "version":
                        "vision-test-v1",
                },
            },

            "sensor_validation": {
                "status":
                    "VALID",

                "reason":
                    "all_checks_passed",
            },

            "sensor_features": {
                "feature_vector_version":
                    "sensor_feature_vector_v1",

                "current": {
                    "soil_moisture_pct":
                        50.0,

                    "temperature_c":
                        25.0,

                    "humidity_pct":
                        60.0,
                },
            },

            "stress_risk": {
                "status":
                    "BLOCKED",

                "stress_risk_score":
                    None,

                "model_version":
                    "UNAVAILABLE",
            },

            "temporal_intelligence": {
                "status":
                    "BLOCKED",

                "reason":
                    "CURRENT_OPERATIONAL_RISK_SCORE_UNAVAILABLE",
            },

            "forecast": {
                "status":
                    "BLOCKED_FORECAST_MODEL_NOT_OPERATIONALLY_VALIDATED",

                "validated":
                    False,

                "future_risk":
                    None,

                "model_version":
                    None,
            },

            "uncertainty": {
                "state":
                    "RECHECK_REQUIRED",

                "reason_codes": [
                    "CONFIDENCE_THRESHOLD_UNAVAILABLE"
                ],
            },

            "decision": {
                "decision_version":
                    "greenpulse.decision_intelligence.v1",

                "decision":
                    "MANUAL_REVIEW",

                "reason_codes": [
                    "UNCERTAINTY_RECHECK_REQUIRED"
                ],
            },

            "decision_safety": {
                "policy_version":
                    "greenpulse.safety_policy.v1",
            },

            "multimodal_model": {
                "status":
                    "BLOCKED",
            },
        },

        "final": {
            "decision":
                "MANUAL_REVIEW",

            "decision_reason_codes": [
                "UNCERTAINTY_RECHECK_REQUIRED"
            ],

            "physical_actuation":
                False,
        },
    }


def legacy_payload():

    return {
        "schema_version":
            "0.6.0",

        "observation_id":
            "OBS-LEGACY-001",

        "timestamp":
            "2026-09-24T10:00:02+00:00",

        "plant_id":
            "P02",

        "crop":
            "tomato",

        "vision": {
            "state":
                "VISUALLY_HEALTHY",

            "predicted_class":
                "Tomato___healthy",

            "confidence":
                0.98,
        },

        "sensor": {
            "status":
                "VALID_SIMULATED",

            "reason":
                "simulation_only",

            "data": {
                "plant_id":
                    "P02",

                "soil_moisture_pct":
                    55.0,
            },
        },

        "water_stress_risk":
            None,

        "forecast":
            None,

        "decision": {
            "action":
                "NO_AUTONOMOUS_ACTION",

            "reason_codes": [
                "WATER_STRESS_MODEL_NOT_VALIDATED"
            ],
        },

        "model": {
            "version":
                "tomato-test-v1",

            "sha256":
                "abc",
        },

        "sensor_window": {
            "trend":
                "FALLING",
        },
    }


class TestAIOutputContract(
    unittest.TestCase
):

    def test_schema_version(self):

        result = build_standard_ai_output(
            master_payload()
        )

        self.assertEqual(
            result[
                "schema_version"
            ],
            SCHEMA_VERSION,
        )


    def test_master_identity_fields(self):

        result = build_standard_ai_output(
            master_payload()
        )

        self.assertEqual(
            result[
                "observation_id"
            ],
            "OBS-MASTER-001",
        )

        self.assertEqual(
            result[
                "plant_id"
            ],
            "P01",
        )


    def test_master_prefers_sensor_timestamp(self):

        result = build_standard_ai_output(
            master_payload()
        )

        self.assertEqual(
            result[
                "timestamp"
            ],
            "2026-09-24T10:00:01+00:00",
        )

        self.assertEqual(
            result[
                "timestamp_source"
            ],
            "SENSOR_TIMESTAMP",
        )


    def test_master_sensor_snapshot(self):

        result = build_standard_ai_output(
            master_payload()
        )

        self.assertTrue(
            result[
                "sensor"
            ][
                "snapshot_available"
            ]
        )

        self.assertEqual(
            result[
                "sensor"
            ][
                "snapshot"
            ][
                "temperature_c"
            ],
            25.0,
        )


    def test_blocked_risk_is_preserved_not_invented(self):

        result = build_standard_ai_output(
            master_payload()
        )

        self.assertEqual(
            result[
                "risk"
            ][
                "status"
            ],
            "BLOCKED",
        )

        self.assertIsNone(
            result[
                "risk"
            ][
                "stress_risk_score"
            ]
        )

        self.assertFalse(
            result[
                "field_availability"
            ][
                "risk_score"
            ]
        )


    def test_missing_temporal_risk_trend_is_null(self):

        result = build_standard_ai_output(
            master_payload()
        )

        self.assertIsNone(
            result[
                "trend"
            ]
        )

        self.assertFalse(
            result[
                "field_availability"
            ][
                "trend"
            ]
        )


    def test_reason_codes_preserved(self):

        result = build_standard_ai_output(
            master_payload()
        )

        self.assertEqual(
            result[
                "decision"
            ],
            "MANUAL_REVIEW",
        )

        self.assertEqual(
            result[
                "reason_codes"
            ],
            [
                "UNCERTAINTY_RECHECK_REQUIRED"
            ],
        )


    def test_model_versions_have_explicit_nulls(self):

        result = build_standard_ai_output(
            master_payload()
        )

        versions = result[
            "model_versions"
        ]

        self.assertEqual(
            versions[
                "vision"
            ],
            "vision-test-v1",
        )

        self.assertIsNone(
            versions[
                "multimodal_fusion"
            ]
        )

        self.assertIsNone(
            versions[
                "forecast"
            ]
        )


    def test_latency_is_explicitly_null_when_not_measured(self):

        result = build_standard_ai_output(
            master_payload()
        )

        self.assertFalse(
            result[
                "latency"
            ][
                "measured"
            ]
        )

        self.assertIsNone(
            result[
                "latency"
            ][
                "total_ms"
            ]
        )


    def test_measured_latency_is_preserved(self):

        result = build_standard_ai_output(
            master_payload(),
            latency_ms=12.5,
        )

        self.assertTrue(
            result[
                "latency"
            ][
                "measured"
            ]
        )

        self.assertEqual(
            result[
                "latency"
            ][
                "total_ms"
            ],
            12.5,
        )


    def test_invalid_latency_rejected(self):

        with self.assertRaises(
            ValueError
        ):

            build_standard_ai_output(
                master_payload(),
                latency_ms=-1,
            )


    def test_legacy_contract_is_supported(self):

        result = build_standard_ai_output(
            legacy_payload()
        )

        self.assertEqual(
            result[
                "contract_metadata"
            ][
                "source_contract"
            ],
            "LEGACY_API_OBSERVATION",
        )

        self.assertEqual(
            result[
                "decision"
            ],
            "NO_AUTONOMOUS_ACTION",
        )

        self.assertEqual(
            result[
                "model_versions"
            ][
                "vision"
            ],
            "tomato-test-v1",
        )


    def test_legacy_sensor_window_not_promoted_to_risk_trend(self):

        result = build_standard_ai_output(
            legacy_payload()
        )

        self.assertIsNone(
            result[
                "trend"
            ]
        )

        self.assertFalse(
            result[
                "scientific_guardrails"
            ][
                "legacy_sensor_window_reinterpreted_as_risk_trend"
            ]
        )


    def test_null_policy_is_versioned_and_exposed(self):

        result = build_standard_ai_output(
            master_payload()
        )

        self.assertEqual(
            result[
                "contract_metadata"
            ][
                "null_policy_version"
            ],
            NULL_POLICY_VERSION,
        )

        self.assertEqual(
            result[
                "contract_metadata"
            ][
                "null_fallback_policy"
            ],
            NULL_FALLBACK_POLICY,
        )


if __name__ == "__main__":
    unittest.main()