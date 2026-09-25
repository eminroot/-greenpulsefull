import unittest
from datetime import datetime, timedelta, timezone

from src.sensor_feature_engineering import (
    FEATURE_NAMES,
    FEATURE_VECTOR_VERSION,
    NORMALIZATION_SCHEMA_VERSION,
    build_sensor_feature_vector,
)


def packet(
    timestamp,
    *,
    plant_id="P01",
    soil=50.0,
    temperature=25.0,
    humidity=60.0,
    source="SIMULATED",
):

    return {
        "plant_id":
            plant_id,

        "timestamp":
            timestamp.isoformat(),

        "soil_moisture_pct":
            soil,

        "temperature_c":
            temperature,

        "humidity_pct":
            humidity,

        "soil_calibrated":
            True,

        "source":
            source,
    }


def observation(
    sensor_packet,
    status="VALID_SIMULATED",
):

    return {
        "sensor": {
            "status":
                status,

            "data":
                sensor_packet,
        }
    }


class TestSensorFeatureEngineering(
    unittest.TestCase
):

    def setUp(self):

        self.now = datetime.now(
            timezone.utc
        ).replace(
            microsecond=0
        )


    def test_current_values_and_stable_schema(self):

        current = packet(
            self.now
        )

        result = build_sensor_feature_vector(
            current,
            [],
        )

        self.assertEqual(
            result[
                "feature_vector"
            ][
                "names"
            ],
            FEATURE_NAMES,
        )

        self.assertEqual(
            result[
                "feature_vector"
            ][
                "length"
            ],
            len(
                FEATURE_NAMES
            ),
        )

        self.assertEqual(
            result[
                "current"
            ][
                "soil_moisture_pct"
            ],
            50.0,
        )


    def test_rolling_average(self):

        current = packet(
            self.now,
            soil=60.0,
            temperature=30.0,
            humidity=70.0,
        )

        p1 = packet(
            self.now
            - timedelta(
                minutes=20
            ),
            soil=40.0,
            temperature=20.0,
            humidity=50.0,
        )

        p2 = packet(
            self.now
            - timedelta(
                minutes=10
            ),
            soil=50.0,
            temperature=25.0,
            humidity=60.0,
        )

        result = build_sensor_feature_vector(
            current,
            [
                observation(
                    p1
                ),
                observation(
                    p2
                ),
            ],
        )

        rolling = result[
            "rolling_window"
        ]

        self.assertTrue(
            rolling[
                "available"
            ]
        )

        self.assertEqual(
            rolling[
                "sample_count"
            ],
            3,
        )

        self.assertAlmostEqual(
            rolling[
                "soil_moisture_pct"
            ],
            50.0,
        )

        self.assertAlmostEqual(
            rolling[
                "temperature_c"
            ],
            25.0,
        )

        self.assertAlmostEqual(
            rolling[
                "humidity_pct"
            ],
            60.0,
        )


    def test_baseline_delta(self):

        current = packet(
            self.now,
            soil=55.0,
            temperature=27.0,
            humidity=65.0,
        )

        baseline = {
            "version":
                "baseline-v1",

            "soil_moisture_pct":
                50.0,

            "temperature_c":
                25.0,

            "humidity_pct":
                60.0,
        }

        result = build_sensor_feature_vector(
            current,
            [],
            baseline=baseline,
        )

        delta = result[
            "baseline_delta"
        ]

        self.assertTrue(
            delta[
                "available"
            ]
        )

        self.assertAlmostEqual(
            delta[
                "soil_moisture_delta"
            ],
            5.0,
        )

        self.assertAlmostEqual(
            delta[
                "temperature_delta"
            ],
            2.0,
        )

        self.assertAlmostEqual(
            delta[
                "humidity_delta"
            ],
            5.0,
        )


    def test_all_three_rates_and_trends(self):

        previous = packet(
            self.now
            - timedelta(
                minutes=30
            ),
            soil=50.0,
            temperature=24.0,
            humidity=70.0,
        )

        current = packet(
            self.now,
            soil=45.0,
            temperature=25.0,
            humidity=60.0,
        )

        result = build_sensor_feature_vector(
            current,
            [
                observation(
                    previous
                )
            ],
        )

        rate = result[
            "rate_of_change"
        ]

        self.assertTrue(
            rate[
                "available"
            ]
        )

        self.assertAlmostEqual(
            rate[
                "soil_moisture_change_per_hour"
            ],
            -10.0,
        )

        self.assertAlmostEqual(
            rate[
                "temperature_change_per_hour"
            ],
            2.0,
        )

        self.assertAlmostEqual(
            rate[
                "humidity_change_per_hour"
            ],
            -20.0,
        )

        self.assertEqual(
            result[
                "trend"
            ][
                "soil_moisture"
            ],
            "FALLING",
        )

        self.assertEqual(
            result[
                "trend"
            ][
                "temperature"
            ],
            "RISING",
        )

        self.assertEqual(
            result[
                "trend"
            ][
                "humidity"
            ],
            "FALLING",
        )


    def test_insufficient_history_is_explicit(self):

        current = packet(
            self.now
        )

        result = build_sensor_feature_vector(
            current,
            [],
        )

        self.assertFalse(
            result[
                "rolling_window"
            ][
                "available"
            ]
        )

        self.assertFalse(
            result[
                "rate_of_change"
            ][
                "available"
            ]
        )

        values = result[
            "feature_vector"
        ][
            "raw_values"
        ]

        self.assertTrue(
            all(
                isinstance(
                    value,
                    float,
                )
                for value in values
            )
        )


    def test_wrong_plant_history_is_ignored(self):

        current = packet(
            self.now,
            plant_id="P01",
        )

        other = packet(
            self.now
            - timedelta(
                minutes=10
            ),
            plant_id="P02",
            soil=1.0,
        )

        result = build_sensor_feature_vector(
            current,
            [
                observation(
                    other
                )
            ],
        )

        self.assertFalse(
            result[
                "rate_of_change"
            ][
                "available"
            ]
        )


    def test_history_order_is_deterministic(self):

        current = packet(
            self.now,
            soil=60.0,
        )

        p1 = packet(
            self.now
            - timedelta(
                minutes=20
            ),
            soil=40.0,
        )

        p2 = packet(
            self.now
            - timedelta(
                minutes=10
            ),
            soil=50.0,
        )

        a = build_sensor_feature_vector(
            current,
            [
                observation(
                    p1
                ),
                observation(
                    p2
                ),
            ],
        )

        b = build_sensor_feature_vector(
            current,
            [
                observation(
                    p2
                ),
                observation(
                    p1
                ),
            ],
        )

        self.assertEqual(
            a[
                "rolling_window"
            ],
            b[
                "rolling_window"
            ],
        )

        self.assertEqual(
            a[
                "rate_of_change"
            ],
            b[
                "rate_of_change"
            ],
        )

        self.assertEqual(
            a[
                "feature_vector"
            ][
                "raw_values"
            ],
            b[
                "feature_vector"
            ][
                "raw_values"
            ],
        )


    def test_versioned_normalization(self):

        current = packet(
            self.now
        )

        parameters = {
            name: {
                "center":
                    0.0,

                "scale":
                    2.0,
            }
            for name in FEATURE_NAMES
        }

        artifact = {
            "schema_version":
                NORMALIZATION_SCHEMA_VERSION,

            "version":
                "norm-test-v1",

            "feature_vector_version":
                FEATURE_VECTOR_VERSION,

            "parameters":
                parameters,
        }

        result = build_sensor_feature_vector(
            current,
            [],
            normalization_artifact=artifact,
        )

        vector = result[
            "feature_vector"
        ]

        self.assertTrue(
            vector[
                "normalization_applied"
            ]
        )

        self.assertEqual(
            vector[
                "normalization_artifact_version"
            ],
            "norm-test-v1",
        )

        self.assertEqual(
            vector[
                "values"
            ][0],
            vector[
                "raw_values"
            ][0]
            / 2.0,
        )


    def test_invalid_normalization_scale_blocked(self):

        current = packet(
            self.now
        )

        parameters = {
            name: {
                "center":
                    0.0,

                "scale":
                    1.0,
            }
            for name in FEATURE_NAMES
        }

        parameters[
            FEATURE_NAMES[0]
        ][
            "scale"
        ] = 0.0

        artifact = {
            "schema_version":
                NORMALIZATION_SCHEMA_VERSION,

            "version":
                "bad",

            "feature_vector_version":
                FEATURE_VECTOR_VERSION,

            "parameters":
                parameters,
        }

        with self.assertRaises(
            ValueError
        ):
            build_sensor_feature_vector(
                current,
                [],
                normalization_artifact=artifact,
            )


    def test_simulated_source_guardrail(self):

        current = packet(
            self.now
        )

        result = build_sensor_feature_vector(
            current,
            [],
        )

        self.assertEqual(
            result[
                "provenance"
            ][
                "source"
            ],
            "SIMULATED",
        )

        self.assertFalse(
            result[
                "scientific_guardrails"
            ][
                "simulated_sensor_is_real_sensor_evidence"
            ]
        )

        self.assertFalse(
            result[
                "scientific_guardrails"
            ][
                "physical_action_authorized"
            ]
        )


if __name__ == "__main__":
    unittest.main()