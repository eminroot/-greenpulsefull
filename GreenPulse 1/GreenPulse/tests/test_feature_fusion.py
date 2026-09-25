import unittest
from datetime import datetime, timezone

import numpy as np

from src.visual_features import (
    extract_visual_features,
)

from src.plant_baseline import (
    build_plant_baseline,
    compute_plant_delta,
)

from src.sensor_feature_engineering import (
    build_sensor_feature_vector,
)

from src.feature_fusion import (
    FUSION_FEATURE_NAMES,
    TEMPORAL_FEATURE_NAMES,
    build_multimodal_feature_vector,
)


def make_visual(
    value=100,
    confidence=0.9,
):

    image = np.full(
        (16, 16, 3),
        value,
        dtype=np.uint8,
    )

    return extract_visual_features(
        image,
        visual_confidence=confidence,
        confidence_source="classification",
    )


def make_delta(
    visual,
    plant_id="P01",
):

    healthy = make_visual(
        90,
        0.95,
    )

    observations = [
        {
            "observation_id":
                f"H{i}",

            "plant_id":
                plant_id,

            "is_healthy":
                True,

            "visual_features":
                healthy,
        }
        for i in range(3)
    ]

    baseline = build_plant_baseline(
        observations,
        plant_id=plant_id,
    )

    return compute_plant_delta(
        visual,
        baseline,
    )


def make_sensor(
    plant_id="P01",
):

    now = datetime.now(
        timezone.utc
    ).replace(
        microsecond=0
    )

    packet = {
        "plant_id":
            plant_id,

        "timestamp":
            now.isoformat(),

        "soil_moisture_pct":
            50.0,

        "temperature_c":
            25.0,

        "humidity_pct":
            60.0,

        "soil_calibrated":
            True,

        "source":
            "SIMULATED",
    }

    return build_sensor_feature_vector(
        packet,
        [],
    )


def make_temporal():

    return {
        "feature_vector_version":
            "temporal_feature_vector_v1",

        "feature_vector": {
            "names":
                list(
                    TEMPORAL_FEATURE_NAMES
                ),

            "values": [
                1.0,
                0.2,
                0.05,
                2.0,
            ],
        },
    }


class TestFeatureFusion(
    unittest.TestCase
):

    def test_stable_feature_schema(self):

        visual = make_visual()

        sensor = make_sensor()

        delta = make_delta(
            visual
        )

        result = build_multimodal_feature_vector(
            visual_features=visual,
            sensor_features=sensor,
            plant_delta=delta,
            temporal_features=None,
            time_sync_status="SYNCED",
        )

        self.assertEqual(
            result[
                "feature_vector"
            ][
                "names"
            ],
            FUSION_FEATURE_NAMES,
        )

        self.assertEqual(
            result[
                "feature_vector"
            ][
                "length"
            ],
            len(
                FUSION_FEATURE_NAMES
            ),
        )

        self.assertTrue(
            all(
                np.isfinite(
                    result[
                        "feature_vector"
                    ][
                        "values"
                    ]
                )
            )
        )


    def test_sensor_simulation_indicator_not_fused(self):

        joined = " ".join(
            FUSION_FEATURE_NAMES
        )

        self.assertNotIn(
            "source_is_simulated",
            joined,
        )


    def test_disease_class_not_fused(self):

        joined = " ".join(
            FUSION_FEATURE_NAMES
        ).lower()

        self.assertNotIn(
            "disease_class",
            joined,
        )

        self.assertNotIn(
            "predicted_class",
            joined,
        )


    def test_gradcam_not_fused(self):

        joined = " ".join(
            FUSION_FEATURE_NAMES
        ).lower()

        self.assertNotIn(
            "gradcam",
            joined,
        )

        self.assertNotIn(
            "heatmap",
            joined,
        )


    def test_missing_temporal_is_explicit(self):

        visual = make_visual()

        sensor = make_sensor()

        result = build_multimodal_feature_vector(
            visual_features=visual,
            sensor_features=sensor,
            plant_delta=None,
            temporal_features=None,
            time_sync_status="SYNCED",
        )

        self.assertFalse(
            result[
                "modalities"
            ][
                "temporal"
            ]
        )

        self.assertEqual(
            result[
                "feature_vector"
            ][
                "values"
            ][
                -1
            ],
            0.0,
        )


    def test_temporal_features_are_included(self):

        visual = make_visual()

        sensor = make_sensor()

        temporal = make_temporal()

        result = build_multimodal_feature_vector(
            visual_features=visual,
            sensor_features=sensor,
            plant_delta=None,
            temporal_features=temporal,
            time_sync_status="SYNCED",
        )

        self.assertTrue(
            result[
                "modalities"
            ][
                "temporal"
            ]
        )

        self.assertEqual(
            result[
                "feature_vector"
            ][
                "values"
            ][
                -1
            ],
            1.0,
        )


    def test_unsynchronized_inputs_are_blocked(self):

        visual = make_visual()

        sensor = make_sensor()

        with self.assertRaises(
            ValueError
        ):

            build_multimodal_feature_vector(
                visual_features=visual,
                sensor_features=sensor,
                plant_delta=None,
                temporal_features=None,
                time_sync_status="NOT_SYNCED",
            )


    def test_plant_identity_mismatch_blocked(self):

        visual = make_visual()

        sensor = make_sensor(
            plant_id="P01"
        )

        delta = make_delta(
            visual,
            plant_id="P02",
        )

        with self.assertRaisesRegex(
            ValueError,
            "PLANT_ID_MISMATCH",
        ):

            build_multimodal_feature_vector(
                visual_features=visual,
                sensor_features=sensor,
                plant_delta=delta,
                temporal_features=None,
                time_sync_status="SYNCED",
            )


    def test_output_is_deterministic(self):

        visual = make_visual()

        sensor = make_sensor()

        delta = make_delta(
            visual
        )

        first = build_multimodal_feature_vector(
            visual_features=visual,
            sensor_features=sensor,
            plant_delta=delta,
            temporal_features=None,
            time_sync_status="SYNCED",
        )

        second = build_multimodal_feature_vector(
            visual_features=visual,
            sensor_features=sensor,
            plant_delta=delta,
            temporal_features=None,
            time_sync_status="SYNCED",
        )

        self.assertEqual(
            first,
            second,
        )


    def test_invalid_temporal_version_blocked(self):

        visual = make_visual()

        sensor = make_sensor()

        temporal = make_temporal()

        temporal[
            "feature_vector_version"
        ] = "wrong"

        with self.assertRaises(
            ValueError
        ):

            build_multimodal_feature_vector(
                visual_features=visual,
                sensor_features=sensor,
                plant_delta=None,
                temporal_features=temporal,
                time_sync_status="SYNCED",
            )


    def test_no_operational_probability_or_actuation(self):

        visual = make_visual()

        sensor = make_sensor()

        result = build_multimodal_feature_vector(
            visual_features=visual,
            sensor_features=sensor,
            plant_delta=None,
            temporal_features=None,
            time_sync_status="SYNCED",
        )

        guardrails = result[
            "scientific_guardrails"
        ]

        self.assertFalse(
            guardrails[
                "fusion_model_trained"
            ]
        )

        self.assertFalse(
            guardrails[
                "water_stress_probability_produced"
            ]
        )

        self.assertFalse(
            guardrails[
                "physical_action_authorized"
            ]
        )


if __name__ == "__main__":
    unittest.main()