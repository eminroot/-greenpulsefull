import unittest

from src.closed_loop_intelligence import (
    FOLLOWUP_SCHEMA_VERSION,
    SCHEMA_VERSION,
    analyze_closed_loop_outcome,
    build_followup_plan,
)


COMMAND_ID = (
    "123e4567-e89b-12d3-a456-426614174000"
)


def simulated_action(
    state="EXECUTED",
):

    return {
        "schema_version":
            "greenpulse.hardware_action_state.v1",

        "command_id":
            COMMAND_ID,

        "observation_id":
            "OBS-ACTION",

        "plant_id":
            "P01",

        "action_state":
            state,

        "state_timestamp":
            "2026-09-24T12:05:00+00:00",

        "simulated":
            True,

        "real_hardware_ack_validated":
            False,

        "physical_actuation":
            False,
    }


def output(
    observation_id,
    timestamp,
    *,
    risk_score=None,
    moisture=50.0,
    temperature=25.0,
    humidity=60.0,
):

    risk = (
        None
        if risk_score is None
        else {
            "status":
                "AVAILABLE",

            "stress_risk_score":
                risk_score,
        }
    )

    return {
        "schema_version":
            "greenpulse.standard_ai_output.v1",

        "observation_id":
            observation_id,

        "plant_id":
            "P01",

        "timestamp":
            timestamp,

        "risk":
            risk,

        "sensor": {
            "snapshot": {
                "soil_moisture_pct":
                    moisture,

                "temperature_c":
                    temperature,

                "humidity_pct":
                    humidity,
            }
        },
    }


class TestClosedLoopIntelligence(
    unittest.TestCase
):

    def test_schema_versions(self):

        self.assertEqual(
            SCHEMA_VERSION,
            "greenpulse.closed_loop_intelligence.v1",
        )

        self.assertEqual(
            FOLLOWUP_SCHEMA_VERSION,
            "greenpulse.closed_loop_followup_plan.v1",
        )


    def test_synthetic_executed_action_can_plan_test_followup(self):

        result = build_followup_plan(
            action_state=
                simulated_action(),

            delay_seconds=
                600,

            test_only=
                True,
        )

        self.assertEqual(
            result[
                "status"
            ],
            "SYNTHETIC_FOLLOWUP_PLANNED",
        )

        self.assertFalse(
            result[
                "real_intervention_verified"
            ]
        )

        self.assertFalse(
            result[
                "scheduler_execution_performed"
            ]
        )


    def test_nonexecuted_action_does_not_schedule_followup(self):

        result = build_followup_plan(
            action_state=
                simulated_action(
                    state="FAILED"
                ),

            delay_seconds=
                600,

            test_only=
                True,
        )

        self.assertEqual(
            result[
                "status"
            ],
            "FOLLOWUP_NOT_SCHEDULED",
        )


    def test_unverified_real_path_is_blocked(self):

        action = simulated_action()

        action[
            "simulated"
        ] = False

        result = build_followup_plan(
            action_state=
                action,

            delay_seconds=
                600,

            test_only=
                False,
        )

        self.assertEqual(
            result[
                "status"
            ],
            "FOLLOWUP_BLOCKED",
        )

        self.assertEqual(
            result[
                "reason"
            ],
            "REAL_INTERVENTION_NOT_VERIFIED",
        )


    def test_synthetic_before_after_risk_comparison(self):

        result = analyze_closed_loop_outcome(
            action_state=
                simulated_action(),

            before_output=
                output(
                    "OBS-BEFORE",
                    "2026-09-24T12:00:00+00:00",
                    risk_score=80.0,
                ),

            after_output=
                output(
                    "OBS-AFTER",
                    "2026-09-24T12:15:00+00:00",
                    risk_score=60.0,
                ),

            test_only=
                True,
        )

        self.assertEqual(
            result[
                "risk"
            ][
                "delta_after_minus_before"
            ],
            -20.0,
        )

        self.assertFalse(
            result[
                "validated_outcome"
            ]
        )

        self.assertFalse(
            result[
                "intervention_success_assumed"
            ]
        )


    def test_sensor_response_is_descriptive_only(self):

        result = analyze_closed_loop_outcome(
            action_state=
                simulated_action(),

            before_output=
                output(
                    "OBS-BEFORE",
                    "2026-09-24T12:00:00+00:00",
                    moisture=40.0,
                ),

            after_output=
                output(
                    "OBS-AFTER",
                    "2026-09-24T12:15:00+00:00",
                    moisture=55.0,
                ),

            test_only=
                True,
        )

        self.assertEqual(
            result[
                "sensor_response"
            ][
                "soil_moisture_delta_pct_points"
            ],
            15.0,
        )

        self.assertFalse(
            result[
                "causal_effect_claimed"
            ]
        )


    def test_missing_risk_is_preserved(self):

        result = analyze_closed_loop_outcome(
            action_state=
                simulated_action(),

            before_output=
                output(
                    "OBS-BEFORE",
                    "2026-09-24T12:00:00+00:00",
                ),

            after_output=
                output(
                    "OBS-AFTER",
                    "2026-09-24T12:15:00+00:00",
                ),

            test_only=
                True,
        )

        self.assertIsNone(
            result[
                "risk"
            ][
                "before"
            ]
        )

        self.assertIsNone(
            result[
                "risk"
            ][
                "after"
            ]
        )

        self.assertIsNone(
            result[
                "risk"
            ][
                "delta_after_minus_before"
            ]
        )


    def test_synthetic_outcome_not_eligible_for_analytics(self):

        result = analyze_closed_loop_outcome(
            action_state=
                simulated_action(),

            before_output=
                output(
                    "OBS-BEFORE",
                    "2026-09-24T12:00:00+00:00",
                    risk_score=80.0,
                ),

            after_output=
                output(
                    "OBS-AFTER",
                    "2026-09-24T12:15:00+00:00",
                    risk_score=60.0,
                ),

            test_only=
                True,
        )

        self.assertFalse(
            result[
                "eligible_for_analytics"
            ]
        )

        self.assertFalse(
            result[
                "eligible_for_future_model_improvement"
            ]
        )


    def test_plant_mismatch_rejected(self):

        after = output(
            "OBS-AFTER",
            "2026-09-24T12:15:00+00:00",
        )

        after[
            "plant_id"
        ] = "P02"

        with self.assertRaises(
            ValueError
        ):

            analyze_closed_loop_outcome(
                action_state=
                    simulated_action(),

                before_output=
                    output(
                        "OBS-BEFORE",
                        "2026-09-24T12:00:00+00:00",
                    ),

                after_output=
                    after,

                test_only=
                    True,
            )


    def test_invalid_chronology_rejected(self):

        with self.assertRaises(
            ValueError
        ):

            analyze_closed_loop_outcome(
                action_state=
                    simulated_action(),

                before_output=
                    output(
                        "OBS-BEFORE",
                        "2026-09-24T12:10:00+00:00",
                    ),

                after_output=
                    output(
                        "OBS-AFTER",
                        "2026-09-24T12:15:00+00:00",
                    ),

                test_only=
                    True,
            )


    def test_unverified_action_never_becomes_validated_outcome(self):

        action = simulated_action()

        action[
            "simulated"
        ] = False

        result = analyze_closed_loop_outcome(
            action_state=
                action,

            before_output=
                output(
                    "OBS-BEFORE",
                    "2026-09-24T12:00:00+00:00",
                    risk_score=80.0,
                ),

            after_output=
                output(
                    "OBS-AFTER",
                    "2026-09-24T12:15:00+00:00",
                    risk_score=60.0,
                ),

            test_only=
                False,
        )

        self.assertEqual(
            result[
                "outcome_status"
            ],
            "INSUFFICIENT_INTERVENTION_EVIDENCE",
        )

        self.assertFalse(
            result[
                "validated_outcome"
            ]
        )


if __name__ == "__main__":
    unittest.main()