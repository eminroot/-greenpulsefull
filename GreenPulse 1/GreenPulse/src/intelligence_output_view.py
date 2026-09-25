from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping, Optional


SCHEMA_VERSION = (
    "greenpulse.intelligence_output_view.v1"
)


BACKEND_FIELDS = (
    "plant_state",
    "confidence",
    "risk",
    "trend",
    "forecast",
    "sensors",
    "uncertainty",
    "decision",
    "reasons",
    "model_version",
    "latency",
    "system_status",
)


FRONTEND_WIDGETS = (
    "live_or_annotated_image",
    "risk_gauge",
    "risk_trend",
    "predicted_risk_horizon",
    "sensor_cards",
    "decision_explanation",
    "last_action",
    "before_after_intervention",
    "sustainability_score",
    "system_health",
)


def _mapping_or_empty(
    value: Any,
) -> dict[str, Any]:

    if isinstance(
        value,
        Mapping,
    ):
        return dict(value)

    return {}


def _first(
    source: Mapping[str, Any],
    *keys: str,
) -> Any:

    for key in keys:

        if key in source:
            return source[key]

    return None


def build_intelligence_output_view(
    observation: Mapping[str, Any],
    *,
    image: Optional[Mapping[str, Any]] = None,
    last_action: Optional[Mapping[str, Any]] = None,
    intervention: Optional[Mapping[str, Any]] = None,
    sustainability: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:

    if not isinstance(
        observation,
        Mapping,
    ):
        raise ValueError(
            "observation must be a mapping."
        )

    original = deepcopy(
        observation
    )

    obs = dict(
        observation
    )

    vision = _mapping_or_empty(
        obs.get(
            "vision"
        )
    )

    risk_section = _mapping_or_empty(
        obs.get(
            "risk"
        )
    )

    forecast_section = _mapping_or_empty(
        obs.get(
            "forecast"
        )
    )

    decision_section = _mapping_or_empty(
        obs.get(
            "decision"
        )
    )

    uncertainty_section = _mapping_or_empty(
        obs.get(
            "uncertainty"
        )
    )

    system_section = _mapping_or_empty(
        obs.get(
            "system"
        )
    )

    backend = {
        "plant_state":
            _first(
                obs,
                "plant_state",
                "plant_status",
            ),

        "confidence":
            (
                _first(
                    obs,
                    "confidence",
                )
                if _first(
                    obs,
                    "confidence",
                )
                is not None
                else _first(
                    vision,
                    "confidence",
                )
            ),

        "risk":
            (
                _first(
                    obs,
                    "risk_score",
                    "risk",
                )
                if not isinstance(
                    obs.get(
                        "risk"
                    ),
                    Mapping,
                )
                else _first(
                    risk_section,
                    "risk_score",
                    "score",
                    "value",
                )
            ),

        "trend":
            _first(
                obs,
                "trend",
            ),

        "forecast":
            (
                obs.get(
                    "forecast"
                )
                if obs.get(
                    "forecast"
                )
                is not None
                else None
            ),

        "sensors":
            _first(
                obs,
                "sensors",
                "sensor_readings",
            ),

        "uncertainty":
            (
                obs.get(
                    "uncertainty"
                )
                if "uncertainty" in obs
                else None
            ),

        "decision":
            (
                _first(
                    obs,
                    "decision"
                )
                if not isinstance(
                    obs.get(
                        "decision"
                    ),
                    Mapping,
                )
                else _first(
                    decision_section,
                    "decision",
                    "action",
                    "state",
                )
            ),

        "reasons":
            (
                _first(
                    obs,
                    "reasons",
                    "reason",
                )
                if _first(
                    obs,
                    "reasons",
                    "reason",
                )
                is not None
                else _first(
                    decision_section,
                    "reasons",
                    "reason",
                )
            ),

        "model_version":
            _first(
                obs,
                "model_version",
                "model_versions",
            ),

        "latency":
            _first(
                obs,
                "latency",
                "latency_ms",
            ),

        "system_status":
            (
                _first(
                    obs,
                    "system_status",
                )
                if _first(
                    obs,
                    "system_status",
                )
                is not None
                else _first(
                    system_section,
                    "status",
                    "system_status",
                )
            ),
    }

    image_payload = (
        dict(image)
        if isinstance(
            image,
            Mapping,
        )
        else {
            "available":
                False,

            "image":
                None,
        }
    )

    action_payload = (
        dict(last_action)
        if isinstance(
            last_action,
            Mapping,
        )
        else {
            "available":
                False,

            "action":
                None,
        }
    )

    intervention_payload = (
        dict(intervention)
        if isinstance(
            intervention,
            Mapping,
        )
        else {
            "available":
                False,

            "before":
                None,

            "after":
                None,
        }
    )

    sustainability_payload = (
        dict(sustainability)
        if isinstance(
            sustainability,
            Mapping,
        )
        else {
            "available":
                False,

            "score":
                None,

            "measured":
                None,

            "estimated":
                None,
        }
    )

    frontend = {
        "live_or_annotated_image":
            image_payload,

        "risk_gauge": {
            "value":
                backend[
                    "risk"
                ],
        },

        "risk_trend": {
            "trend":
                backend[
                    "trend"
                ],
        },

        "predicted_risk_horizon": {
            "forecast":
                backend[
                    "forecast"
                ],
        },

        "sensor_cards": {
            "sensors":
                backend[
                    "sensors"
                ],
        },

        "decision_explanation": {
            "decision":
                backend[
                    "decision"
                ],

            "reasons":
                backend[
                    "reasons"
                ],
        },

        "last_action":
            action_payload,

        "before_after_intervention":
            intervention_payload,

        "sustainability_score":
            sustainability_payload,

        "system_health": {
            "system_status":
                backend[
                    "system_status"
                ],

            "uncertainty":
                backend[
                    "uncertainty"
                ],

            "latency":
                backend[
                    "latency"
                ],
        },
    }

    missing_backend_values = [
        field
        for field in BACKEND_FIELDS
        if backend[
            field
        ] is None
    ]

    if observation != original:
        raise RuntimeError(
            "Input observation mutated."
        )

    return {
        "schema_version":
            SCHEMA_VERSION,

        "backend":
            backend,

        "frontend":
            frontend,

        "availability": {
            "backend_fields_present":
                len(
                    BACKEND_FIELDS
                )
                - len(
                    missing_backend_values
                ),

            "backend_fields_total":
                len(
                    BACKEND_FIELDS
                ),

            "missing_backend_values":
                missing_backend_values,

            "frontend_widget_contracts_present":
                len(
                    FRONTEND_WIDGETS
                ),

            "frontend_widget_contracts_total":
                len(
                    FRONTEND_WIDGETS
                ),
        },

        "claim_boundary": {
            "frontend_rendering_implemented":
                False,

            "widget_payload_contract_complete":
                True,

            "missing_values_fabricated":
                False,

            "null_value_means_operationally_validated":
                False,
        },
    }