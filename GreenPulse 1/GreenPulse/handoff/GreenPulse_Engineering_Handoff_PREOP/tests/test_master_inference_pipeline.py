import tempfile
import unittest
from datetime import (
    datetime,
    timezone,
)
from pathlib import Path

from PIL import Image

from src.master_inference_pipeline import (
    OUTPUT_SCHEMA_VERSION,
    PIPELINE_VERSION,
    STAGE_ORDER,
    run_master_inference_pipeline,
)


class FakeVision:

    def predict(
        self,
        image_path,
        crop,
    ):

        return {
            "schema_version":
                "synthetic-test",

            "status":
                "SUCCESS",

            "crop":
                crop,

            "vision": {
                "state":
                    "DISEASE_PATTERN_PREDICTED",

                "predicted_class":
                    "Tomato___synthetic_test_class",

                "confidence":
                    0.9,

                "confidence_calibrated":
                    False,
            },

            "water_stress_risk":
                None,

            "forecast":
                None,

            "decision":
                "NO_AUTONOMOUS_ACTION",
        }


def make_image(
    directory,
):

    path = (
        Path(directory)
        / "test.png"
    )

    Image.new(
        "RGB",
        (224, 224),
        (120, 140, 110),
    ).save(
        path
    )

    return path


def sensor_packet(
    *,
    source="REAL",
):

    now = datetime.now(
        timezone.utc
    ).isoformat()

    return {
        "plant_id":
            "TEST-PLANT-01",

        "timestamp":
            now,

        "source":
            source,

        "soil_moisture_pct":
            50.0,

        "temperature_c":
            25.0,

        "humidity_pct":
            60.0,

        "soil_calibrated":
            True,
    }


def run_pipeline(
    image_path,
    *,
    engine=None,
    source="REAL",
):

    packet = sensor_packet(
        source=source
    )

    return run_master_inference_pipeline(
        observation_id=
            "OBS-TEST-001",

        plant_id=
            "TEST-PLANT-01",

        crop=
            "tomato",

        image_path=
            image_path,

        image_captured_at=
            packet[
                "timestamp"
            ],

        sensor_packet=
            packet,

        sensor_observations=[
            packet
        ],

        vision_engine=
            engine,
    )


class TestMasterInferencePipeline(
    unittest.TestCase
):

    def test_versioned_output(self):

        with tempfile.TemporaryDirectory() as tmp:

            result = run_pipeline(
                make_image(tmp)
            )

        self.assertEqual(
            result[
                "schema_version"
            ],
            OUTPUT_SCHEMA_VERSION,
        )

        self.assertEqual(
            result[
                "pipeline_version"
            ],
            PIPELINE_VERSION,
        )


    def test_stage_order_contract(self):

        with tempfile.TemporaryDirectory() as tmp:

            result = run_pipeline(
                make_image(tmp)
            )

        self.assertEqual(
            result[
                "stage_order"
            ],
            list(
                STAGE_ORDER
            ),
        )


    def test_no_engine_is_blocked_not_faked(self):

        with tempfile.TemporaryDirectory() as tmp:

            result = run_pipeline(
                make_image(tmp)
            )

        self.assertEqual(
            result[
                "stages"
            ][
                "vision_inference"
            ][
                "status"
            ],
            "BLOCKED",
        )


    def test_fake_engine_allows_visual_feature_contract(self):

        with tempfile.TemporaryDirectory() as tmp:

            result = run_pipeline(
                make_image(tmp),
                engine=FakeVision(),
            )

        visual = result[
            "stages"
        ][
            "visual_features"
        ]

        self.assertEqual(
            visual[
                "feature_vector_version"
            ],
            "visual_feature_vector_v1",
        )


    def test_fusion_features_can_be_constructed_without_real_model(self):

        with tempfile.TemporaryDirectory() as tmp:

            result = run_pipeline(
                make_image(tmp),
                engine=FakeVision(),
            )

        fused = result[
            "stages"
        ][
            "multimodal_feature_fusion"
        ]

        self.assertEqual(
            fused[
                "feature_vector_version"
            ],
            "multimodal_feature_vector_v1",
        )

        self.assertEqual(
            fused[
                "feature_vector"
            ][
                "length"
            ],
            54,
        )


    def test_real_fusion_model_absence_blocks_model_stage(self):

        with tempfile.TemporaryDirectory() as tmp:

            result = run_pipeline(
                make_image(tmp),
                engine=FakeVision(),
            )

        self.assertEqual(
            result[
                "stages"
            ][
                "multimodal_model"
            ][
                "status"
            ],
            "BLOCKED",
        )


    def test_operational_risk_is_not_fabricated(self):

        with tempfile.TemporaryDirectory() as tmp:

            result = run_pipeline(
                make_image(tmp),
                engine=FakeVision(),
            )

        risk = result[
            "stages"
        ][
            "stress_risk"
        ]

        self.assertEqual(
            risk[
                "status"
            ],
            "BLOCKED",
        )

        self.assertIsNone(
            risk[
                "stress_risk_score"
            ]
        )


    def test_disease_classification_not_converted_to_stress(self):

        with tempfile.TemporaryDirectory() as tmp:

            result = run_pipeline(
                make_image(tmp),
                engine=FakeVision(),
            )

        self.assertFalse(
            result[
                "scientific_guardrails"
            ][
                "disease_classification_is_water_stress"
            ]
        )

        self.assertEqual(
            result[
                "stages"
            ][
                "vision_sensor_conflict"
            ][
                "status"
            ],
            "CONFLICT_NOT_EVALUABLE",
        )


    def test_simulated_sensor_blocks_operational_path(self):

        with tempfile.TemporaryDirectory() as tmp:

            result = run_pipeline(
                make_image(tmp),
                engine=FakeVision(),
                source="SIMULATED",
            )

        self.assertEqual(
            result[
                "stages"
            ][
                "sensor_validation"
            ][
                "status"
            ],
            "VALID_SIMULATED",
        )

        self.assertEqual(
            result[
                "stages"
            ][
                "uncertainty"
            ][
                "state"
            ],
            "RECHECK_REQUIRED",
        )


    def test_current_safety_policy_never_dispatches(self):

        with tempfile.TemporaryDirectory() as tmp:

            result = run_pipeline(
                make_image(tmp),
                engine=FakeVision(),
            )

        self.assertFalse(
            result[
                "final"
            ][
                "hardware_dispatch_permitted"
            ]
        )

        self.assertFalse(
            result[
                "final"
            ][
                "physical_actuation"
            ]
        )


    def test_no_operational_forecast_claim(self):

        with tempfile.TemporaryDirectory() as tmp:

            result = run_pipeline(
                make_image(tmp),
                engine=FakeVision(),
            )

        forecast = result[
            "stages"
        ][
            "forecast"
        ]

        self.assertFalse(
            forecast[
                "validated"
            ]
        )

        self.assertIsNone(
            result[
                "final"
            ][
                "forecast"
            ]
        )


    def test_explanation_uses_no_llm(self):

        with tempfile.TemporaryDirectory() as tmp:

            result = run_pipeline(
                make_image(tmp),
                engine=FakeVision(),
            )

        self.assertFalse(
            result[
                "stages"
            ][
                "explainability"
            ][
                "explanation_generation"
            ][
                "llm_used"
            ]
        )


if __name__ == "__main__":
    unittest.main()