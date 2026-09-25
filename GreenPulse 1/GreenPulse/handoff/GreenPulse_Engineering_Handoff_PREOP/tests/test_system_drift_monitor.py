import copy
import unittest

from src.system_drift_monitor import (
    SCHEMA_VERSION,
    categorical_distribution,
    evaluate_system_drift,
    numeric_summary,
    total_variation_distance,
)


def policy():

    return {
        "schema_version":
            "greenpulse.drift_monitoring_policy.v1",

        "policy_status":
            "TEST_ONLY",

        "thresholds": {
            "confidence_mean_drop_absolute":
                0.15,

            "prediction_total_variation_distance":
                0.20,

            "risk_mean_relative_shift":
                0.25,

            "sensor_mean_relative_shift":
                0.25,
        },

        "workflow": {
            "warning_action":
                "REVIEW_RETRAINING_WORKFLOW",

            "automatic_model_deployment_allowed":
                False,
        },

        "production_baseline": {
            "status":
                "NOT_AVAILABLE",

            "source":
                None,
        },
    }


def baseline():

    return {
        "prediction_labels": [
            "HEALTHY",
            "HEALTHY",
            "STRESS",
            "HEALTHY",
        ],

        "confidences": [
            0.90,
            0.92,
            0.88,
            0.91,
        ],

        "risks": [
            20,
            22,
            25,
            21,
        ],

        "sensors": {
            "soil_moisture": [
                40,
                42,
                41,
                43,
            ],

            "temperature": [
                25,
                25,
                26,
                25,
            ],
        },
    }


def stable_current():

    return {
        "prediction_labels": [
            "HEALTHY",
            "HEALTHY",
            "STRESS",
            "HEALTHY",
        ],

        "confidences": [
            0.89,
            0.90,
            0.88,
            0.89,
        ],

        "risks": [
            21,
            22,
            24,
            22,
        ],

        "sensors": {
            "soil_moisture": [
                41,
                42,
                40,
                43,
            ],

            "temperature": [
                25,
                26,
                25,
                25,
            ],
        },

        "runtime_errors": [],

        "resource_metrics": {
            "rss_mb":
                500,

            "cpu_percent":
                20,
        },
    }


class TestSystemDriftMonitor(
    unittest.TestCase
):

    def test_schema_version(self):

        result = evaluate_system_drift(
            policy=policy(),
            baseline=baseline(),
            current=stable_current(),
        )

        self.assertEqual(
            result["schema_version"],
            SCHEMA_VERSION,
        )


    def test_numeric_summary(self):

        result = numeric_summary(
            [1, 2, 3]
        )

        self.assertEqual(
            result["mean"],
            2.0,
        )


    def test_categorical_distribution(self):

        result = categorical_distribution(
            ["A", "A", "B", "A"]
        )

        self.assertEqual(
            result["A"],
            0.75,
        )


    def test_total_variation_distance(self):

        result = total_variation_distance(
            {
                "A": 1.0,
            },
            {
                "B": 1.0,
            },
        )

        self.assertEqual(
            result,
            1.0,
        )


    def test_no_baseline_blocks_drift_evaluation(self):

        result = evaluate_system_drift(
            policy=policy(),
            baseline=None,
            current=stable_current(),
        )

        self.assertEqual(
            result["status"],
            "BASELINE_REQUIRED",
        )

        self.assertFalse(
            result["drift"]["evaluated"]
        )


    def test_stable_data_no_warning(self):

        result = evaluate_system_drift(
            policy=policy(),
            baseline=baseline(),
            current=stable_current(),
        )

        self.assertEqual(
            result["status"],
            "NO_DRIFT_WARNING",
        )


    def test_confidence_drop_warning(self):

        current = stable_current()

        current["confidences"] = [
            0.50,
            0.55,
            0.60,
            0.50,
        ]

        result = evaluate_system_drift(
            policy=policy(),
            baseline=baseline(),
            current=current,
        )

        codes = [
            item["code"]
            for item
            in result["drift"]["warnings"]
        ]

        self.assertIn(
            "CONFIDENCE_DROP",
            codes,
        )


    def test_prediction_shift_warning(self):

        current = stable_current()

        current["prediction_labels"] = [
            "STRESS",
            "STRESS",
            "STRESS",
            "STRESS",
        ]

        result = evaluate_system_drift(
            policy=policy(),
            baseline=baseline(),
            current=current,
        )

        codes = [
            item["code"]
            for item
            in result["drift"]["warnings"]
        ]

        self.assertIn(
            "PREDICTION_DISTRIBUTION_SHIFT",
            codes,
        )


    def test_sensor_shift_warning(self):

        current = stable_current()

        current["sensors"][
            "soil_moisture"
        ] = [
            15,
            16,
            14,
            15,
        ]

        result = evaluate_system_drift(
            policy=policy(),
            baseline=baseline(),
            current=current,
        )

        codes = [
            item["code"]
            for item
            in result["drift"]["warnings"]
        ]

        self.assertIn(
            "FEATURE_DISTRIBUTION_CHANGE",
            codes,
        )


    def test_risk_shift_warning(self):

        current = stable_current()

        current["risks"] = [
            60,
            62,
            65,
            61,
        ]

        result = evaluate_system_drift(
            policy=policy(),
            baseline=baseline(),
            current=current,
        )

        codes = [
            item["code"]
            for item
            in result["drift"]["warnings"]
        ]

        self.assertIn(
            "RISK_DISTRIBUTION_SHIFT",
            codes,
        )


    def test_runtime_errors_are_monitored(self):

        current = stable_current()

        current["runtime_errors"] = [
            "CAMERA_TIMEOUT",
            "API_ERROR",
        ]

        result = evaluate_system_drift(
            policy=policy(),
            baseline=baseline(),
            current=current,
        )

        self.assertEqual(
            result[
                "monitoring"
            ][
                "runtime_errors"
            ][
                "count"
            ],
            2,
        )


    def test_resource_metrics_are_monitored(self):

        result = evaluate_system_drift(
            policy=policy(),
            baseline=baseline(),
            current=stable_current(),
        )

        self.assertEqual(
            result[
                "monitoring"
            ][
                "resource_metrics"
            ][
                "rss_mb"
            ],
            500,
        )


    def test_warning_never_enables_auto_deploy(self):

        current = stable_current()

        current["confidences"] = [
            0.1,
            0.1,
            0.1,
            0.1,
        ]

        result = evaluate_system_drift(
            policy=policy(),
            baseline=baseline(),
            current=current,
        )

        self.assertTrue(
            result[
                "workflow"
            ][
                "review_required"
            ]
        )

        self.assertFalse(
            result[
                "workflow"
            ][
                "automatic_model_deployment_allowed"
            ]
        )


    def test_inputs_not_mutated(self):

        base = baseline()
        current = stable_current()

        base_copy = copy.deepcopy(
            base
        )

        current_copy = copy.deepcopy(
            current
        )

        evaluate_system_drift(
            policy=policy(),
            baseline=base,
            current=current,
        )

        self.assertEqual(
            base,
            base_copy,
        )

        self.assertEqual(
            current,
            current_copy,
        )


if __name__ == "__main__":
    unittest.main()