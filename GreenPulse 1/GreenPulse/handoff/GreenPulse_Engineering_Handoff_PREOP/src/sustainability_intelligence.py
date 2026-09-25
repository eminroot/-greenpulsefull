from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Optional


SCHEMA_VERSION = (
    "greenpulse.sustainability_intelligence.v1"
)

POLICY_SCHEMA_VERSION = (
    "greenpulse.sustainability_metrics_policy.v1"
)


MEASURED = "MEASURED"
ESTIMATED = "ESTIMATED"
UNAVAILABLE = "UNAVAILABLE"


def _nonnegative_optional(
    value: Optional[float],
    name: str,
) -> Optional[float]:

    if value is None:
        return None

    number = float(value)

    if number < 0:
        raise ValueError(
            f"{name} must be non-negative."
        )

    return number


def _metric(
    *,
    name: str,
    value: Optional[float],
    unit: str,
    value_type: str,
    available: bool,
    methodology: str,
) -> dict[str, Any]:

    if value_type not in {
        MEASURED,
        ESTIMATED,
        UNAVAILABLE,
    }:
        raise ValueError(
            "Unsupported value_type."
        )

    if not available:
        value = None
        value_type = UNAVAILABLE

    return {
        "metric_name":
            name,

        "value":
            value,

        "unit":
            unit,

        "value_type":
            value_type,

        "available":
            available,

        "methodology":
            methodology,
    }


def validate_policy(
    policy: Mapping[str, Any],
) -> None:

    if (
        policy.get(
            "schema_version"
        )
        != POLICY_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unsupported sustainability policy schema."
        )

    claim_policy = policy.get(
        "claim_policy"
    )

    if not isinstance(
        claim_policy,
        Mapping,
    ):
        raise ValueError(
            "claim_policy missing."
        )

    required_true = (
        "measured_and_estimated_must_be_explicit",
        "water_savings_require_validated_baseline",
        "carbon_savings_require_emissions_factor",
        "carbon_savings_require_energy_methodology",
        "gamification_must_not_modify_engineering_metrics",
    )

    for key in required_true:

        if claim_policy.get(key) is not True:
            raise ValueError(
                f"{key} must remain true."
            )


def compute_sustainability_metrics(
    *,
    policy: Mapping[str, Any],
    water_usage_liters: Optional[float],
    water_usage_type: Optional[str],
    intervention_count: int,
    energy_kwh: Optional[float],
    energy_type: Optional[str],
) -> dict[str, Any]:

    validate_policy(
        policy
    )

    if intervention_count < 0:
        raise ValueError(
            "intervention_count must be non-negative."
        )

    water_usage = _nonnegative_optional(
        water_usage_liters,
        "water_usage_liters",
    )

    energy = _nonnegative_optional(
        energy_kwh,
        "energy_kwh",
    )

    if (
        water_usage is not None
        and water_usage_type
        not in {
            MEASURED,
            ESTIMATED,
        }
    ):
        raise ValueError(
            "water_usage_type must be MEASURED or ESTIMATED."
        )

    if (
        energy is not None
        and energy_type
        not in {
            MEASURED,
            ESTIMATED,
        }
    ):
        raise ValueError(
            "energy_type must be MEASURED or ESTIMATED."
        )

    baseline = policy.get(
        "validated_baseline",
        {},
    )

    baseline_valid = (
        baseline.get(
            "status"
        )
        == "VALIDATED"
    )

    baseline_water = (
        _nonnegative_optional(
            baseline.get(
                "water_liters"
            ),
            "baseline water_liters",
        )
        if baseline_valid
        else None
    )

    baseline_energy = (
        _nonnegative_optional(
            baseline.get(
                "energy_kwh"
            ),
            "baseline energy_kwh",
        )
        if baseline_valid
        else None
    )

    metrics = {}

    metrics[
        "water_usage"
    ] = _metric(
        name="water_usage",
        value=water_usage,
        unit="liters",
        value_type=(
            water_usage_type
            if water_usage is not None
            else UNAVAILABLE
        ),
        available=(
            water_usage is not None
        ),
        methodology=(
            "Direct/derived operational water usage supplied by caller."
        ),
    )

    water_saved_available = (
        baseline_valid
        and baseline_water is not None
        and water_usage is not None
    )

    water_saved = (
        max(
            0.0,
            baseline_water
            - water_usage,
        )
        if water_saved_available
        else None
    )

    metrics[
        "water_saved_vs_validated_baseline"
    ] = _metric(
        name="water_saved_vs_validated_baseline",
        value=water_saved,
        unit="liters",
        value_type=ESTIMATED,
        available=water_saved_available,
        methodology=(
            "Validated baseline water usage minus current operational water usage."
        ),
    )

    metrics[
        "intervention_count"
    ] = _metric(
        name="intervention_count",
        value=float(
            intervention_count
        ),
        unit="count",
        value_type=MEASURED,
        available=True,
        methodology=(
            "Count derived from action/intervention log records."
        ),
    )

    energy_available = (
        energy is not None
    )

    metrics[
        "energy_usage"
    ] = _metric(
        name="energy_usage",
        value=energy,
        unit="kWh",
        value_type=(
            energy_type
            if energy_available
            else UNAVAILABLE
        ),
        available=energy_available,
        methodology=(
            "Operational energy measurement or documented estimate supplied by caller."
        ),
    )

    resource_efficiency_available = (
        baseline_valid
        and baseline_water is not None
        and baseline_water > 0
        and water_usage is not None
    )

    resource_efficiency = (
        max(
            0.0,
            min(
                100.0,
                (
                    (
                        baseline_water
                        - water_usage
                    )
                    / baseline_water
                )
                * 100.0,
            ),
        )
        if resource_efficiency_available
        else None
    )

    metrics[
        "resource_efficiency_score"
    ] = _metric(
        name="resource_efficiency_score",
        value=resource_efficiency,
        unit="percent",
        value_type=ESTIMATED,
        available=resource_efficiency_available,
        methodology=(
            "Relative water-use reduction versus validated baseline; "
            "bounded to 0-100."
        ),
    )

    carbon_policy = policy.get(
        "carbon_methodology",
        {},
    )

    emissions_factor = (
        _nonnegative_optional(
            carbon_policy.get(
                "emissions_factor_kg_co2e_per_kwh"
            ),
            "emissions factor",
        )
    )

    emissions_source = (
        carbon_policy.get(
            "emissions_factor_source"
        )
    )

    methodology_documented = (
        carbon_policy.get(
            "energy_methodology_documented"
        )
        is True
    )

    carbon_available = all(
        (
            baseline_valid,
            baseline_energy is not None,
            energy is not None,
            emissions_factor is not None,
            isinstance(
                emissions_source,
                str,
            ),
            bool(
                str(
                    emissions_source
                ).strip()
            )
            if emissions_source is not None
            else False,
            methodology_documented,
        )
    )

    carbon_saved = (
        max(
            0.0,
            baseline_energy
            - energy,
        )
        * emissions_factor
        if carbon_available
        else None
    )

    metrics[
        "carbon_saved_vs_validated_baseline"
    ] = _metric(
        name="carbon_saved_vs_validated_baseline",
        value=carbon_saved,
        unit="kgCO2e",
        value_type=ESTIMATED,
        available=carbon_available,
        methodology=(
            "Energy reduction versus validated baseline multiplied by "
            "documented emissions factor."
        ),
    )

    return {
        "schema_version":
            SCHEMA_VERSION,

        "policy_schema_version":
            POLICY_SCHEMA_VERSION,

        "metrics":
            metrics,

        "baseline": {
            "validated":
                baseline_valid,

            "source":
                baseline.get(
                    "source"
                ),
        },

        "carbon_methodology": {
            "emissions_factor_available":
                emissions_factor
                is not None,

            "emissions_factor_source_available":
                bool(
                    emissions_source
                ),

            "energy_methodology_documented":
                methodology_documented,
        },

        "claim_boundary": {
            "measured_vs_estimated_explicit":
                True,

            "water_savings_claim_available":
                water_saved_available,

            "carbon_savings_claim_available":
                carbon_available,

            "validated_baseline_available":
                baseline_valid,

            "gamification_changes_engineering_metrics":
                False,
        },
    }


def build_dashboard_sustainability_view(
    result: Mapping[str, Any],
    *,
    badge: Optional[str] = None,
) -> dict[str, Any]:

    original = deepcopy(
        result
    )

    view = {
        "schema_version":
            "greenpulse.sustainability_dashboard_view.v1",

        "engineering_metrics":
            deepcopy(
                result[
                    "metrics"
                ]
            ),

        "gamification": {
            "badge":
                badge,
        },

        "claim_boundary":
            deepcopy(
                result[
                    "claim_boundary"
                ]
            ),
    }

    if result != original:
        raise RuntimeError(
            "Sustainability result mutated."
        )

    return view