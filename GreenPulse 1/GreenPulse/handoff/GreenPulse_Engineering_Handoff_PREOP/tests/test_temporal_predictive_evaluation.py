import unittest

from src.temporal_predictive_evaluation import (
    REAL_SCOPE,
    SCHEMA_VERSION,
    SYNTHETIC_SCOPE,
    compare_forecast_vs_naive,
    compare_single_frame_vs_temporal,
    evaluate_alert_lead_time,
    evaluate_temporal_predictive_system,
    regression_metrics,
)


class TestTemporalPredictiveEvaluation(
    unittest.TestCase
):

    def test_schema_version(self):

        self.assertEqual(
            SCHEMA_VERSION,
            "greenpulse.temporal_predictive_evaluation.v1",
        )


    def test_perfect_regression_metrics(self):

        result = regression_metrics(
            [1, 2, 3],
            [1, 2, 3],
        )

        self.assertEqual(
            result["mae"],
            0.0,
        )

        self.assertEqual(
            result["rmse"],
            0.0,
        )


    def test_regression_length_mismatch(self):

        with self.assertRaises(
            ValueError
        ):
            regression_metrics(
                [1, 2],
                [1],
            )


    def test_temporal_comparison(self):

        result = (
            compare_single_frame_vs_temporal(
                y_true=[
                    0, 0, 1, 1
                ],
                single_frame=[
                    0, 1, 1, 0
                ],
                temporal_verified=[
                    0, 0, 1, 1
                ],
            )
        )

        self.assertTrue(
            result[
                "temporal_f1_not_worse"
            ]
        )


    def test_forecast_beats_naive(self):

        result = compare_forecast_vs_naive(
            y_true=[10, 20, 30],
            forecast=[11, 19, 30],
            naive=[10, 10, 20],
        )

        self.assertTrue(
            result[
                "forecast_better_than_naive"
            ]
        )


    def test_forecast_not_better_than_naive(self):

        result = compare_forecast_vs_naive(
            y_true=[10, 20, 30],
            forecast=[0, 0, 0],
            naive=[10, 20, 30],
        )

        self.assertFalse(
            result[
                "forecast_better_than_naive"
            ]
        )


    def test_positive_lead_time(self):

        result = evaluate_alert_lead_time(
            event_flags=[
                0, 0, 0, 1, 0
            ],
            forecast_alerts=[
                0, 1, 0, 0, 0
            ],
            step_minutes=10,
            action_window_steps=3,
        )

        self.assertEqual(
            result[
                "mean_positive_lead_time_minutes"
            ],
            20.0,
        )


    def test_false_alarm_detected(self):

        result = evaluate_alert_lead_time(
            event_flags=[
                0, 0, 0, 0
            ],
            forecast_alerts=[
                1, 0, 1, 0
            ],
            step_minutes=10,
            action_window_steps=2,
        )

        self.assertEqual(
            result[
                "false_alarm_rate"
            ],
            1.0,
        )


    def test_synthetic_scope_blocks_claim(self):

        result = evaluate_temporal_predictive_system(
            decision_truth=[
                0, 0, 1, 1
            ],
            single_frame_decisions=[
                0, 1, 1, 0
            ],
            temporal_decisions=[
                0, 0, 1, 1
            ],
            forecast_truth=[
                10, 20, 30
            ],
            forecast_predictions=[
                11, 19, 30
            ],
            naive_predictions=[
                10, 10, 20
            ],
            event_flags=[
                0, 0, 0, 1
            ],
            forecast_alerts=[
                0, 1, 0, 0
            ],
            step_minutes=10,
            action_window_steps=3,
            max_false_alarm_rate=0.25,
            evidence_scope=SYNTHETIC_SCOPE,
        )

        self.assertFalse(
            result[
                "claim_boundary"
            ][
                "forecast_benefit_claim_permitted"
            ]
        )


    def test_real_scope_can_permit_claim(self):

        result = evaluate_temporal_predictive_system(
            decision_truth=[
                0, 0, 1, 1
            ],
            single_frame_decisions=[
                0, 1, 1, 0
            ],
            temporal_decisions=[
                0, 0, 1, 1
            ],
            forecast_truth=[
                10, 20, 30
            ],
            forecast_predictions=[
                11, 19, 30
            ],
            naive_predictions=[
                10, 10, 20
            ],
            event_flags=[
                0, 0, 0, 1
            ],
            forecast_alerts=[
                0, 1, 0, 0
            ],
            step_minutes=10,
            action_window_steps=3,
            max_false_alarm_rate=0.25,
            evidence_scope=REAL_SCOPE,
        )

        self.assertTrue(
            result[
                "claim_boundary"
            ][
                "forecast_benefit_claim_permitted"
            ]
        )


    def test_high_false_alarm_blocks_real_claim(self):

        result = evaluate_temporal_predictive_system(
            decision_truth=[
                0, 0, 1, 1
            ],
            single_frame_decisions=[
                0, 1, 1, 0
            ],
            temporal_decisions=[
                0, 0, 1, 1
            ],
            forecast_truth=[
                10, 20, 30
            ],
            forecast_predictions=[
                11, 19, 30
            ],
            naive_predictions=[
                10, 10, 20
            ],
            event_flags=[
                0, 0, 0, 1, 0, 0
            ],
            forecast_alerts=[
                1, 1, 0, 0, 0, 1
            ],
            step_minutes=10,
            action_window_steps=2,
            max_false_alarm_rate=0.20,
            evidence_scope=REAL_SCOPE,
        )

        self.assertFalse(
            result[
                "claim_boundary"
            ][
                "forecast_benefit_claim_permitted"
            ]
        )


    def test_invalid_false_alarm_threshold(self):

        with self.assertRaises(
            ValueError
        ):
            evaluate_temporal_predictive_system(
                decision_truth=[0, 1],
                single_frame_decisions=[0, 1],
                temporal_decisions=[0, 1],
                forecast_truth=[1, 2],
                forecast_predictions=[1, 2],
                naive_predictions=[1, 2],
                event_flags=[0, 1],
                forecast_alerts=[1, 0],
                step_minutes=10,
                action_window_steps=1,
                max_false_alarm_rate=1.5,
                evidence_scope=SYNTHETIC_SCOPE,
            )


    def test_invalid_scope_rejected(self):

        with self.assertRaises(
            ValueError
        ):
            evaluate_temporal_predictive_system(
                decision_truth=[0, 1],
                single_frame_decisions=[0, 1],
                temporal_decisions=[0, 1],
                forecast_truth=[1, 2],
                forecast_predictions=[1, 2],
                naive_predictions=[1, 2],
                event_flags=[0, 1],
                forecast_alerts=[1, 0],
                step_minutes=10,
                action_window_steps=1,
                max_false_alarm_rate=0.5,
                evidence_scope="UNKNOWN",
            )


    def test_invalid_step_minutes_rejected(self):

        with self.assertRaises(
            ValueError
        ):
            evaluate_alert_lead_time(
                event_flags=[0, 1],
                forecast_alerts=[1, 0],
                step_minutes=0,
                action_window_steps=1,
            )


if __name__ == "__main__":
    unittest.main()