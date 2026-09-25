import json
import tempfile
import unittest
from pathlib import Path

from src.adaptive_sampling import (
    DECISION_SCHEMA_VERSION,
    POLICY_SCHEMA_VERSION,
    evaluate_adaptive_sampling,
    load_sampling_policy,
    validate_sampling_policy,
)


def context(
    *,
    risk=None,
    forecast=None,
    trend=None,
    stable=False,
):

    return {
        "plant_id":
            "P01",

        "observation_id":
            "OBS-001",

        "timestamp":
            "2026-09-24T12:00:00+00:00",

        "risk_score":
            risk,

        "forecast_risk_score":
            forecast,

        "trend_state":
            trend,

        "stable_healthy_confirmed":
            stable,
    }


class TestAdaptiveSampling(
    unittest.TestCase
):

    def test_schema_versions(self):

        self.assertEqual(
            POLICY_SCHEMA_VERSION,
            "greenpulse.adaptive_sampling_policy.v1",
        )

        self.assertEqual(
            DECISION_SCHEMA_VERSION,
            "greenpulse.adaptive_sampling_decision.v1",
        )


    def test_default_policy_valid(self):

        policy = load_sampling_policy()

        self.assertEqual(
            policy[
                "policy_status"
            ],
            "DEVELOPMENT_ONLY_UNVALIDATED",
        )


    def test_stable_confirmed_uses_low_frequency(self):

        result = evaluate_adaptive_sampling(
            context(
                risk=10,
                forecast=10,
                trend="STABLE",
                stable=True,
            )
        )

        self.assertEqual(
            result[
                "sampling_level"
            ],
            "STABLE_HEALTHY",
        )

        self.assertEqual(
            result[
                "interval_seconds"
            ],
            900.0,
        )


    def test_rising_trend_increases_frequency(self):

        result = evaluate_adaptive_sampling(
            context(
                risk=20,
                forecast=20,
                trend="RISING",
                stable=False,
            )
        )

        self.assertEqual(
            result[
                "sampling_level"
            ],
            "ELEVATED",
        )

        self.assertEqual(
            result[
                "interval_seconds"
            ],
            120.0,
        )


    def test_high_risk_uses_high_frequency(self):

        result = evaluate_adaptive_sampling(
            context(
                risk=80,
            )
        )

        self.assertEqual(
            result[
                "sampling_level"
            ],
            "HIGH",
        )

        self.assertEqual(
            result[
                "interval_seconds"
            ],
            30.0,
        )


    def test_high_forecast_uses_high_frequency(self):

        result = evaluate_adaptive_sampling(
            context(
                risk=10,
                forecast=85,
            )
        )

        self.assertEqual(
            result[
                "sampling_level"
            ],
            "HIGH",
        )

        self.assertIn(
            "HIGH_FORECAST_RISK",
            result[
                "reason_codes"
            ],
        )


    def test_disease_healthy_alone_cannot_reduce_frequency(self):

        payload = context(
            risk=None,
            forecast=None,
            trend=None,
            stable=False,
        )

        payload[
            "vision_class"
        ] = "healthy"


        result = evaluate_adaptive_sampling(
            payload
        )


        self.assertEqual(
            result[
                "sampling_level"
            ],
            "NORMAL",
        )

        self.assertFalse(
            result[
                "scientific_guardrails"
            ][
                "disease_healthy_label_alone_reduces_frequency"
            ]
        )


    def test_next_observation_is_computed(self):

        result = evaluate_adaptive_sampling(
            context(
                risk=80,
            )
        )

        self.assertEqual(
            result[
                "next_observation_at"
            ],
            "2026-09-24T12:00:30+00:00",
        )


    def test_invalid_risk_rejected(self):

        with self.assertRaises(
            ValueError
        ):

            evaluate_adaptive_sampling(
                context(
                    risk=101,
                )
            )


    def test_bad_interval_order_rejected(self):

        policy = load_sampling_policy()

        policy[
            "intervals_seconds"
        ][
            "high"
        ] = 1000


        with self.assertRaises(
            ValueError
        ):

            validate_sampling_policy(
                policy
            )


    def test_policy_does_not_claim_resource_savings(self):

        result = evaluate_adaptive_sampling(
            context(
                risk=80,
            )
        )

        guardrails = result[
            "scientific_guardrails"
        ]


        self.assertFalse(
            guardrails[
                "energy_savings_claimed"
            ]
        )

        self.assertFalse(
            guardrails[
                "cpu_savings_claimed"
            ]
        )

        self.assertFalse(
            guardrails[
                "response_quality_preservation_validated"
            ]
        )


if __name__ == "__main__":
    unittest.main()