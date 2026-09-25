import unittest

from src.decision_intelligence import (
    DECISION_VERSION,
    evaluate_decision,
)


def decision(
    **overrides,
):

    args = {
        "vision_result": {
            "state":
                "NORMAL",

            "validated":
                True,

            "vision_sensor_conflict":
                False,
        },

        "fusion_risk": {
            "band":
                "NO_ACTION",

            "thresholds_validated":
                True,

            "stress_risk_score":
                20.0,
        },

        "forecast": {
            "status":
                "FORECAST_AVAILABLE",

            "validated":
                True,

            "future_risk":
                22.0,

            "naive_future_risk":
                20.0,
        },

        "temporal_consistency": {
            "state":
                "CONFIRMED_STRESS",
        },

        "uncertainty": {
            "state":
                "CONFIDENT",

            "review_required":
                False,
        },

        "sensor_validity":
            (
                "VALID",
                "all_checks_passed",
            ),

        "safety_state": {
            "action":
                "REQUEST_GATE_OPEN",

            "request_allowed":
                True,

            "validated":
                True,
        },
    }

    args.update(
        overrides
    )

    return evaluate_decision(
        **args
    )


class TestDecisionIntelligence(
    unittest.TestCase
):

    def test_no_action(self):

        result = decision()

        self.assertEqual(
            result[
                "decision"
            ],
            "NO_ACTION",
        )


    def test_monitor_band(self):

        result = decision(
            fusion_risk={
                "band":
                    "MONITOR",

                "thresholds_validated":
                    True,

                "stress_risk_score":
                    45.0,
            }
        )

        self.assertEqual(
            result[
                "decision"
            ],
            "MONITOR",
        )


    def test_warning_band(self):

        result = decision(
            fusion_risk={
                "band":
                    "WARNING",

                "thresholds_validated":
                    True,

                "stress_risk_score":
                    65.0,
            }
        )

        self.assertEqual(
            result[
                "decision"
            ],
            "WARNING",
        )


    def test_logical_irrigation_request_path(self):

        result = decision(
            fusion_risk={
                "band":
                    "ACTION",

                "thresholds_validated":
                    True,

                "stress_risk_score":
                    85.0,
            }
        )

        self.assertEqual(
            result[
                "decision"
            ],
            "IRRIGATION_REQUEST",
        )

        self.assertTrue(
            result[
                "irrigation_request"
            ][
                "created"
            ]
        )

        self.assertFalse(
            result[
                "irrigation_request"
            ][
                "hardware_command"
            ]
        )


    def test_current_safety_gate_blocks_request(self):

        result = decision(
            fusion_risk={
                "band":
                    "ACTION",

                "thresholds_validated":
                    True,

                "stress_risk_score":
                    90.0,
            },

            safety_state={
                "action":
                    "NO_AUTONOMOUS_ACTION",

                "request_allowed":
                    False,

                "validated":
                    True,
            },
        )

        self.assertEqual(
            result[
                "decision"
            ],
            "WARNING",
        )

        self.assertFalse(
            result[
                "irrigation_request"
            ][
                "created"
            ]
        )


    def test_uncertain_routes_recheck(self):

        result = decision(
            uncertainty={
                "state":
                    "UNCERTAIN",

                "review_required":
                    True,
            }
        )

        self.assertEqual(
            result[
                "decision"
            ],
            "RECHECK",
        )


    def test_recheck_required_routes_manual_review(self):

        result = decision(
            uncertainty={
                "state":
                    "RECHECK_REQUIRED",

                "review_required":
                    True,
            }
        )

        self.assertEqual(
            result[
                "decision"
            ],
            "MANUAL_REVIEW",
        )


    def test_conflict_routes_recheck(self):

        result = decision(
            vision_result={
                "state":
                    "HIGH_STRESS",

                "validated":
                    True,

                "vision_sensor_conflict":
                    True,
            }
        )

        self.assertEqual(
            result[
                "decision"
            ],
            "RECHECK",
        )


    def test_missing_sensor_routes_recheck(self):

        result = decision(
            sensor_validity=(
                "MISSING",
                "soil_moisture_pct",
            )
        )

        self.assertEqual(
            result[
                "decision"
            ],
            "RECHECK",
        )


    def test_simulated_sensor_routes_recheck(self):

        result = decision(
            sensor_validity=(
                "VALID_SIMULATED",
                "simulation_only",
            )
        )

        self.assertEqual(
            result[
                "decision"
            ],
            "RECHECK",
        )


    def test_unvalidated_thresholds_route_recheck(self):

        result = decision(
            fusion_risk={
                "band":
                    "ACTION",

                "thresholds_validated":
                    False,

                "stress_risk_score":
                    95.0,
            }
        )

        self.assertEqual(
            result[
                "decision"
            ],
            "RECHECK",
        )


    def test_temporal_recheck_blocks_action(self):

        result = decision(
            fusion_risk={
                "band":
                    "ACTION",

                "thresholds_validated":
                    True,

                "stress_risk_score":
                    90.0,
            },

            temporal_consistency={
                "state":
                    "RECHECK",
            },
        )

        self.assertEqual(
            result[
                "decision"
            ],
            "RECHECK",
        )


    def test_unvalidated_forecast_blocks_irrigation_request(self):

        result = decision(
            fusion_risk={
                "band":
                    "ACTION",

                "thresholds_validated":
                    True,

                "stress_risk_score":
                    90.0,
            },

            forecast={
                "status":
                    "FORECAST_AVAILABLE",

                "validated":
                    False,

                "future_risk":
                    95.0,

                "naive_future_risk":
                    90.0,
            },
        )

        self.assertEqual(
            result[
                "decision"
            ],
            "WARNING",
        )


    def test_same_input_same_output(self):

        first = decision(
            fusion_risk={
                "band":
                    "MONITOR",

                "thresholds_validated":
                    True,

                "stress_risk_score":
                    40.0,
            }
        )

        second = decision(
            fusion_risk={
                "band":
                    "MONITOR",

                "thresholds_validated":
                    True,

                "stress_risk_score":
                    40.0,
            }
        )

        self.assertEqual(
            first,
            second,
        )

        self.assertEqual(
            first[
                "decision_version"
            ],
            DECISION_VERSION,
        )


    def test_layer_never_dispatches_hardware(self):

        result = decision(
            fusion_risk={
                "band":
                    "ACTION",

                "thresholds_validated":
                    True,

                "stress_risk_score":
                    90.0,
            }
        )

        self.assertFalse(
            result[
                "irrigation_request"
            ][
                "dispatch_permitted"
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