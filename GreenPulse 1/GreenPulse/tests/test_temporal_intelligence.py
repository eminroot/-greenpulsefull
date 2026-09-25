import unittest

from src.temporal_intelligence import (
    FEATURE_VECTOR_NAMES,
    build_temporal_features,
)


def observation(
    hour,
    score,
    *,
    plant_id="P01",
    soil=50.0,
    temperature=25.0,
    humidity=60.0,
):

    return {
        "plant_id":
            plant_id,

        "timestamp":
            (
                f"2026-09-24T"
                f"{hour:02d}:00:00+00:00"
            ),

        "validated_observation":
            True,

        "risk_status":
            "SCORE_AVAILABLE",

        "stress_risk_score":
            float(
                score
            ),

        "sensor_values": {
            "soil_moisture_pct":
                float(
                    soil
                ),

            "temperature_c":
                float(
                    temperature
                ),

            "humidity_pct":
                float(
                    humidity
                ),
        },
    }


def validated_threshold_artifact(
    action_probability=0.70,
):

    return {
        "schema_version":
            "greenpulse.risk_calibration.v1",

        "status":
            "VALIDATED",

        "threshold_candidates": {
            "thresholds": {
                "ACTION": {
                    "threshold":
                        float(
                            action_probability
                        )
                }
            }
        },
    }


class TestTemporalIntelligence(
    unittest.TestCase
):

    def test_rising_risk_velocity(self):

        result = build_temporal_features(
            [
                observation(
                    10,
                    20,
                ),
                observation(
                    11,
                    30,
                ),
                observation(
                    12,
                    45,
                ),
            ]
        )

        self.assertEqual(
            result[
                "risk_dynamics"
            ][
                "trend"
            ],
            "RISING",
        )

        self.assertGreater(
            result[
                "risk_dynamics"
            ][
                "velocity"
            ],
            0.0,
        )


    def test_falling_risk_velocity(self):

        result = build_temporal_features(
            [
                observation(
                    10,
                    70,
                ),
                observation(
                    11,
                    60,
                ),
                observation(
                    12,
                    45,
                ),
            ]
        )

        self.assertEqual(
            result[
                "risk_dynamics"
            ][
                "trend"
            ],
            "FALLING",
        )


    def test_stable_deadband(self):

        result = build_temporal_features(
            [
                observation(
                    10,
                    50.0,
                ),
                observation(
                    11,
                    50.2,
                ),
                observation(
                    12,
                    50.4,
                ),
            ],
            risk_velocity_deadband=0.5,
        )

        self.assertEqual(
            result[
                "risk_dynamics"
            ][
                "trend"
            ],
            "STABLE",
        )


    def test_acceleration_is_derived(self):

        result = build_temporal_features(
            [
                observation(
                    10,
                    20,
                ),
                observation(
                    11,
                    30,
                ),
                observation(
                    12,
                    50,
                ),
            ]
        )

        self.assertAlmostEqual(
            result[
                "risk_dynamics"
            ][
                "acceleration"
            ],
            10.0,
        )


    def test_temporal_vector_matches_layer22_contract(self):

        result = build_temporal_features(
            [
                observation(
                    10,
                    20,
                ),
                observation(
                    11,
                    30,
                ),
                observation(
                    12,
                    45,
                ),
            ]
        )

        vector = result[
            "feature_vector"
        ]

        self.assertIsNotNone(
            vector
        )

        self.assertEqual(
            vector[
                "names"
            ],
            FEATURE_VECTOR_NAMES,
        )

        self.assertEqual(
            vector[
                "length"
            ],
            4,
        )


    def test_less_than_three_has_no_fusion_vector(self):

        result = build_temporal_features(
            [
                observation(
                    10,
                    20,
                ),
                observation(
                    11,
                    30,
                ),
            ]
        )

        self.assertEqual(
            result[
                "status"
            ],
            "INSUFFICIENT_HISTORY",
        )

        self.assertIsNone(
            result[
                "feature_vector"
            ]
        )


    def test_sensor_trends_derived(self):

        result = build_temporal_features(
            [
                observation(
                    10,
                    20,
                    soil=60,
                    temperature=24,
                    humidity=65,
                ),
                observation(
                    11,
                    25,
                    soil=55,
                    temperature=25,
                    humidity=62,
                ),
                observation(
                    12,
                    30,
                    soil=50,
                    temperature=26,
                    humidity=59,
                ),
            ],
            sensor_trend_deadbands={
                "soil_moisture_pct":
                    0.1,

                "temperature_c":
                    0.1,

                "humidity_pct":
                    0.1,
            },
        )

        self.assertEqual(
            result[
                "sensor_trends"
            ][
                "soil_moisture_pct"
            ][
                "trend"
            ],
            "FALLING",
        )

        self.assertEqual(
            result[
                "sensor_trends"
            ][
                "temperature_c"
            ][
                "trend"
            ],
            "RISING",
        )


    def test_without_validated_threshold_state_is_recheck(self):

        result = build_temporal_features(
            [
                observation(
                    10,
                    80,
                ),
                observation(
                    11,
                    85,
                ),
                observation(
                    12,
                    90,
                ),
            ],
            threshold_artifact=None,
        )

        self.assertEqual(
            result[
                "temporal_consistency"
            ][
                "state"
            ],
            "RECHECK",
        )


    def test_candidate_threshold_cannot_confirm_stress(self):

        artifact = (
            validated_threshold_artifact()
        )

        artifact[
            "status"
        ] = "CANDIDATE_ONLY"

        result = build_temporal_features(
            [
                observation(
                    10,
                    80,
                ),
                observation(
                    11,
                    85,
                ),
                observation(
                    12,
                    90,
                ),
            ],
            threshold_artifact=
                artifact,
        )

        self.assertEqual(
            result[
                "temporal_consistency"
            ][
                "state"
            ],
            "RECHECK",
        )


    def test_validated_threshold_can_confirm_repeated_stress(self):

        result = build_temporal_features(
            [
                observation(
                    10,
                    65,
                ),
                observation(
                    11,
                    78,
                ),
                observation(
                    12,
                    82,
                ),
            ],
            threshold_artifact=
                validated_threshold_artifact(
                    0.70
                ),
            confirmation_count=2,
        )

        self.assertEqual(
            result[
                "temporal_consistency"
            ][
                "state"
            ],
            "CONFIRMED_STRESS",
        )


    def test_mixed_plant_identity_blocked(self):

        with self.assertRaises(
            ValueError
        ):

            build_temporal_features(
                [
                    observation(
                        10,
                        20,
                        plant_id="P01",
                    ),
                    observation(
                        11,
                        30,
                        plant_id="P02",
                    ),
                    observation(
                        12,
                        40,
                        plant_id="P01",
                    ),
                ]
            )


    def test_unvalidated_observation_blocked(self):

        records = [
            observation(
                10,
                20,
            ),
            observation(
                11,
                30,
            ),
            observation(
                12,
                40,
            ),
        ]

        records[1][
            "validated_observation"
        ] = False

        with self.assertRaises(
            ValueError
        ):

            build_temporal_features(
                records
            )


if __name__ == "__main__":
    unittest.main()