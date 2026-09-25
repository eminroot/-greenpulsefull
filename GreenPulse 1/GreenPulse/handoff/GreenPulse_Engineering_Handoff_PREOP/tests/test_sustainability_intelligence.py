import copy
import unittest

from src.sustainability_intelligence import (
    ESTIMATED,
    MEASURED,
    SCHEMA_VERSION,
    UNAVAILABLE,
    build_dashboard_sustainability_view,
    compute_sustainability_metrics,
)


def policy(
    *,
    validated=False,
    water=None,
    energy=None,
    factor=None,
    source=None,
    methodology=False,
):

    return {
        "schema_version":
            "greenpulse.sustainability_metrics_policy.v1",

        "policy_status":
            "TEST_ONLY",

        "validated_baseline": {
            "status":
                "VALIDATED"
                if validated
                else "NOT_AVAILABLE",

            "water_liters":
                water,

            "energy_kwh":
                energy,

            "source":
                "TEST_VALIDATED_BASELINE"
                if validated
                else None,
        },

        "carbon_methodology": {
            "emissions_factor_kg_co2e_per_kwh":
                factor,

            "emissions_factor_source":
                source,

            "energy_methodology_documented":
                methodology,
        },

        "claim_policy": {
            "measured_and_estimated_must_be_explicit":
                True,

            "water_savings_require_validated_baseline":
                True,

            "carbon_savings_require_emissions_factor":
                True,

            "carbon_savings_require_energy_methodology":
                True,

            "gamification_must_not_modify_engineering_metrics":
                True,
        },
    }


class TestSustainabilityIntelligence(
    unittest.TestCase
):

    def test_schema_version(self):

        self.assertEqual(
            SCHEMA_VERSION,
            "greenpulse.sustainability_intelligence.v1",
        )


    def test_measured_water_usage_explicit(self):

        result = compute_sustainability_metrics(
            policy=policy(),
            water_usage_liters=10,
            water_usage_type=MEASURED,
            intervention_count=2,
            energy_kwh=None,
            energy_type=None,
        )

        metric = result[
            "metrics"
        ][
            "water_usage"
        ]

        self.assertEqual(
            metric["value_type"],
            MEASURED,
        )


    def test_water_savings_blocked_without_baseline(self):

        result = compute_sustainability_metrics(
            policy=policy(),
            water_usage_liters=10,
            water_usage_type=MEASURED,
            intervention_count=2,
            energy_kwh=None,
            energy_type=None,
        )

        metric = result[
            "metrics"
        ][
            "water_saved_vs_validated_baseline"
        ]

        self.assertFalse(
            metric["available"]
        )

        self.assertEqual(
            metric["value_type"],
            UNAVAILABLE,
        )


    def test_water_savings_with_validated_baseline(self):

        result = compute_sustainability_metrics(
            policy=policy(
                validated=True,
                water=20,
            ),
            water_usage_liters=12,
            water_usage_type=MEASURED,
            intervention_count=1,
            energy_kwh=None,
            energy_type=None,
        )

        metric = result[
            "metrics"
        ][
            "water_saved_vs_validated_baseline"
        ]

        self.assertTrue(
            metric["available"]
        )

        self.assertEqual(
            metric["value"],
            8.0,
        )

        self.assertEqual(
            metric["value_type"],
            ESTIMATED,
        )


    def test_intervention_count_is_measured(self):

        result = compute_sustainability_metrics(
            policy=policy(),
            water_usage_liters=None,
            water_usage_type=None,
            intervention_count=3,
            energy_kwh=None,
            energy_type=None,
        )

        metric = result[
            "metrics"
        ][
            "intervention_count"
        ]

        self.assertEqual(
            metric["value"],
            3.0,
        )

        self.assertEqual(
            metric["value_type"],
            MEASURED,
        )


    def test_resource_efficiency_requires_baseline(self):

        result = compute_sustainability_metrics(
            policy=policy(),
            water_usage_liters=10,
            water_usage_type=MEASURED,
            intervention_count=0,
            energy_kwh=None,
            energy_type=None,
        )

        self.assertFalse(
            result[
                "metrics"
            ][
                "resource_efficiency_score"
            ][
                "available"
            ]
        )


    def test_resource_efficiency_score(self):

        result = compute_sustainability_metrics(
            policy=policy(
                validated=True,
                water=20,
            ),
            water_usage_liters=10,
            water_usage_type=MEASURED,
            intervention_count=0,
            energy_kwh=None,
            energy_type=None,
        )

        self.assertEqual(
            result[
                "metrics"
            ][
                "resource_efficiency_score"
            ][
                "value"
            ],
            50.0,
        )


    def test_carbon_blocked_without_factor(self):

        result = compute_sustainability_metrics(
            policy=policy(
                validated=True,
                water=20,
                energy=10,
            ),
            water_usage_liters=10,
            water_usage_type=MEASURED,
            intervention_count=0,
            energy_kwh=8,
            energy_type=MEASURED,
        )

        self.assertFalse(
            result[
                "metrics"
            ][
                "carbon_saved_vs_validated_baseline"
            ][
                "available"
            ]
        )


    def test_carbon_blocked_without_methodology(self):

        result = compute_sustainability_metrics(
            policy=policy(
                validated=True,
                water=20,
                energy=10,
                factor=0.4,
                source="TEST_FACTOR",
                methodology=False,
            ),
            water_usage_liters=10,
            water_usage_type=MEASURED,
            intervention_count=0,
            energy_kwh=8,
            energy_type=MEASURED,
        )

        self.assertFalse(
            result[
                "metrics"
            ][
                "carbon_saved_vs_validated_baseline"
            ][
                "available"
            ]
        )


    def test_carbon_available_with_full_methodology(self):

        result = compute_sustainability_metrics(
            policy=policy(
                validated=True,
                water=20,
                energy=10,
                factor=0.4,
                source="TEST_FACTOR",
                methodology=True,
            ),
            water_usage_liters=10,
            water_usage_type=MEASURED,
            intervention_count=0,
            energy_kwh=8,
            energy_type=MEASURED,
        )

        metric = result[
            "metrics"
        ][
            "carbon_saved_vs_validated_baseline"
        ]

        self.assertTrue(
            metric["available"]
        )

        self.assertAlmostEqual(
            metric["value"],
            0.8,
        )

        self.assertEqual(
            metric["value_type"],
            ESTIMATED,
        )


    def test_negative_usage_rejected(self):

        with self.assertRaises(
            ValueError
        ):
            compute_sustainability_metrics(
                policy=policy(),
                water_usage_liters=-1,
                water_usage_type=MEASURED,
                intervention_count=0,
                energy_kwh=None,
                energy_type=None,
            )


    def test_invalid_measurement_type_rejected(self):

        with self.assertRaises(
            ValueError
        ):
            compute_sustainability_metrics(
                policy=policy(),
                water_usage_liters=1,
                water_usage_type="REAL",
                intervention_count=0,
                energy_kwh=None,
                energy_type=None,
            )


    def test_dashboard_gamification_does_not_change_metrics(self):

        result = compute_sustainability_metrics(
            policy=policy(
                validated=True,
                water=20,
            ),
            water_usage_liters=10,
            water_usage_type=MEASURED,
            intervention_count=1,
            energy_kwh=None,
            energy_type=None,
        )

        original = copy.deepcopy(
            result
        )

        view = build_dashboard_sustainability_view(
            result,
            badge="TEST_BADGE",
        )

        self.assertEqual(
            result,
            original,
        )

        self.assertEqual(
            view[
                "engineering_metrics"
            ],
            result[
                "metrics"
            ],
        )


    def test_current_unvalidated_policy_blocks_savings_claims(self):

        current_policy = {
            "schema_version":
                "greenpulse.sustainability_metrics_policy.v1",

            "policy_status":
                "DEVELOPMENT_ONLY_UNVALIDATED",

            "validated_baseline": {
                "status":
                    "NOT_AVAILABLE",

                "water_liters":
                    None,

                "energy_kwh":
                    None,

                "source":
                    None,
            },

            "carbon_methodology": {
                "emissions_factor_kg_co2e_per_kwh":
                    None,

                "emissions_factor_source":
                    None,

                "energy_methodology_documented":
                    False,
            },

            "claim_policy": {
                "measured_and_estimated_must_be_explicit":
                    True,

                "water_savings_require_validated_baseline":
                    True,

                "carbon_savings_require_emissions_factor":
                    True,

                "carbon_savings_require_energy_methodology":
                    True,

                "gamification_must_not_modify_engineering_metrics":
                    True,
            },
        }

        result = compute_sustainability_metrics(
            policy=current_policy,
            water_usage_liters=None,
            water_usage_type=None,
            intervention_count=0,
            energy_kwh=None,
            energy_type=None,
        )

        self.assertFalse(
            result[
                "claim_boundary"
            ][
                "water_savings_claim_available"
            ]
        )

        self.assertFalse(
            result[
                "claim_boundary"
            ][
                "carbon_savings_claim_available"
            ]
        )


if __name__ == "__main__":
    unittest.main()