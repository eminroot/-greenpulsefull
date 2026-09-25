from __future__ import annotations

from typing import Any, Mapping


DECISION_VERSION = (
    "greenpulse.decision_intelligence.v1"
)


OUTPUTS = {
    "NO_ACTION",
    "MONITOR",
    "RECHECK",
    "WARNING",
    "IRRIGATION_REQUEST",
    "MANUAL_REVIEW",
}


VISION_STATES = {
    "NORMAL",
    "HIGH_STRESS",
    "UNKNOWN",
}


RISK_BANDS = {
    "NO_ACTION",
    "MONITOR",
    "WARNING",
    "ACTION",
    "UNKNOWN",
}


UNCERTAINTY_STATES = {
    "CONFIDENT",
    "UNCERTAIN",
    "RECHECK_REQUIRED",
}


TEMPORAL_STATES = {
    "CONFIRMED_STRESS",
    "RECHECK",
}


VALID_SENSOR_STATUSES = {
    "VALID",
    "VALID_SIMULATED",
    "MISSING",
    "INVALID",
    "STALE",
}


def _strict_bool(
    value: Any,
    name: str,
) -> bool:

    if type(value) is not bool:

        raise ValueError(
            f"{name} must be boolean."
        )

    return value


def _finite_risk_score(
    value: Any,
    name: str,
) -> float:

    if isinstance(
        value,
        bool,
    ):

        raise ValueError(
            f"{name} must be numeric."
        )

    value = float(
        value
    )

    if not (
        0.0
        <= value
        <= 100.0
    ):

        raise ValueError(
            f"{name} must be in [0, 100]."
        )

    return value


def _normalize_vision(
    vision_result: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:

    if not isinstance(
        vision_result,
        Mapping,
    ):

        raise ValueError(
            "vision_result must be a mapping."
        )


    state = vision_result.get(
        "state"
    )


    if state not in VISION_STATES:

        raise ValueError(
            "Unsupported vision state."
        )


    validated = _strict_bool(
        vision_result.get(
            "validated"
        ),
        "vision_result.validated",
    )


    conflict = vision_result.get(
        "vision_sensor_conflict",
        False,
    )


    conflict = _strict_bool(
        conflict,
        "vision_result.vision_sensor_conflict",
    )


    return {
        "state":
            state,

        "validated":
            validated,

        "vision_sensor_conflict":
            conflict,
    }


def _normalize_risk(
    fusion_risk: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:

    if not isinstance(
        fusion_risk,
        Mapping,
    ):

        raise ValueError(
            "fusion_risk must be a mapping."
        )


    band = fusion_risk.get(
        "band"
    )


    if band not in RISK_BANDS:

        raise ValueError(
            "Unsupported fusion risk band."
        )


    thresholds_validated = _strict_bool(
        fusion_risk.get(
            "thresholds_validated"
        ),
        "fusion_risk.thresholds_validated",
    )


    score = fusion_risk.get(
        "stress_risk_score"
    )


    if score is not None:

        score = _finite_risk_score(
            score,
            "stress_risk_score",
        )


    return {
        "band":
            band,

        "thresholds_validated":
            thresholds_validated,

        "stress_risk_score":
            score,
    }


def _normalize_forecast(
    forecast: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:

    if not isinstance(
        forecast,
        Mapping,
    ):

        raise ValueError(
            "forecast must be a mapping."
        )


    status = forecast.get(
        "status"
    )


    if not isinstance(
        status,
        str,
    ) or not status:

        raise ValueError(
            "forecast.status is required."
        )


    validated = _strict_bool(
        forecast.get(
            "validated"
        ),
        "forecast.validated",
    )


    future_risk = forecast.get(
        "future_risk"
    )


    if future_risk is not None:

        future_risk = _finite_risk_score(
            future_risk,
            "forecast.future_risk",
        )


    naive_future_risk = forecast.get(
        "naive_future_risk"
    )


    if naive_future_risk is not None:

        naive_future_risk = _finite_risk_score(
            naive_future_risk,
            "forecast.naive_future_risk",
        )


    return {
        "status":
            status,

        "validated":
            validated,

        "future_risk":
            future_risk,

        "naive_future_risk":
            naive_future_risk,
    }


def _normalize_temporal(
    temporal_consistency: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:

    if not isinstance(
        temporal_consistency,
        Mapping,
    ):

        raise ValueError(
            "temporal_consistency must be a mapping."
        )


    if (
        "temporal_consistency"
        in temporal_consistency
        and isinstance(
            temporal_consistency[
                "temporal_consistency"
            ],
            Mapping,
        )
    ):

        payload = temporal_consistency[
            "temporal_consistency"
        ]

    else:

        payload = temporal_consistency


    state = payload.get(
        "state"
    )


    if state not in TEMPORAL_STATES:

        raise ValueError(
            "Unsupported temporal consistency state."
        )


    return {
        "state":
            state,
    }


def _normalize_uncertainty(
    uncertainty: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:

    if not isinstance(
        uncertainty,
        Mapping,
    ):

        raise ValueError(
            "uncertainty must be a mapping."
        )


    state = uncertainty.get(
        "state"
    )


    if state not in UNCERTAINTY_STATES:

        raise ValueError(
            "Unsupported uncertainty state."
        )


    return {
        "state":
            state,

        "review_required":
            bool(
                uncertainty.get(
                    "review_required",
                    state != "CONFIDENT",
                )
            ),
    }


def _normalize_sensor(
    sensor_validity: Any,
) -> dict[str, Any]:

    if isinstance(
        sensor_validity,
        Mapping,
    ):

        status = sensor_validity.get(
            "status"
        )

        reason = sensor_validity.get(
            "reason"
        )


    elif (
        isinstance(
            sensor_validity,
            (tuple, list),
        )
        and len(
            sensor_validity
        ) == 2
    ):

        status = sensor_validity[0]

        reason = sensor_validity[1]


    else:

        raise ValueError(
            "sensor_validity must be mapping "
            "or (status, reason)."
        )


    if status not in VALID_SENSOR_STATUSES:

        raise ValueError(
            "Unsupported sensor validity status."
        )


    return {
        "status":
            status,

        "reason":
            (
                ""
                if reason is None
                else str(
                    reason
                )
            ),
    }


def _normalize_safety(
    safety_state: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:

    if not isinstance(
        safety_state,
        Mapping,
    ):

        raise ValueError(
            "safety_state must be a mapping."
        )


    action = safety_state.get(
        "action"
    )


    if (
        not isinstance(
            action,
            str,
        )
        or not action
    ):

        raise ValueError(
            "safety_state.action is required."
        )


    request_allowed = safety_state.get(
        "request_allowed",
        False,
    )


    if type(
        request_allowed
    ) is not bool:

        raise ValueError(
            "safety_state.request_allowed "
            "must be boolean."
        )


    validated = safety_state.get(
        "validated",
        False,
    )


    if type(
        validated
    ) is not bool:

        raise ValueError(
            "safety_state.validated "
            "must be boolean."
        )


    logical_request_allowed = (
        request_allowed
        and validated
        and action
        != "NO_AUTONOMOUS_ACTION"
    )


    return {
        "action":
            action,

        "request_allowed":
            request_allowed,

        "validated":
            validated,

        "logical_request_allowed":
            logical_request_allowed,
    }


def evaluate_decision(
    *,
    vision_result: Mapping[
        str,
        Any,
    ],
    fusion_risk: Mapping[
        str,
        Any,
    ],
    forecast: Mapping[
        str,
        Any,
    ],
    temporal_consistency: Mapping[
        str,
        Any,
    ],
    uncertainty: Mapping[
        str,
        Any,
    ],
    sensor_validity: Any,
    safety_state: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:

    vision = _normalize_vision(
        vision_result
    )

    risk = _normalize_risk(
        fusion_risk
    )

    forecast_result = (
        _normalize_forecast(
            forecast
        )
    )

    temporal = _normalize_temporal(
        temporal_consistency
    )

    uncertainty_result = (
        _normalize_uncertainty(
            uncertainty
        )
    )

    sensor = _normalize_sensor(
        sensor_validity
    )

    safety = _normalize_safety(
        safety_state
    )


    reason_codes = []


    # Highest-priority uncertainty state:
    # explicit human/manual inspection path.
    if (
        uncertainty_result[
            "state"
        ]
        == "RECHECK_REQUIRED"
    ):

        decision = "MANUAL_REVIEW"

        reason_codes.append(
            "UNCERTAINTY_RECHECK_REQUIRED"
        )


    # Cross-modal contradiction must never
    # be forced into actuation.
    elif vision[
        "vision_sensor_conflict"
    ]:

        decision = "RECHECK"

        reason_codes.append(
            "VISION_SENSOR_CONFLICT"
        )


    # Operational sensor path requires VALID,
    # not simulated/missing/stale/invalid.
    elif sensor[
        "status"
    ] != "VALID":

        decision = "RECHECK"

        reason_codes.append(
            "SENSOR_NOT_OPERATIONALLY_VALID"
        )

        reason_codes.append(
            f"SENSOR_STATUS_{sensor['status']}"
        )


    # Vision state itself must have an explicit
    # validated upstream interpretation.
    elif (
        not vision[
            "validated"
        ]
        or vision[
            "state"
        ]
        == "UNKNOWN"
    ):

        decision = "RECHECK"

        reason_codes.append(
            "VISION_SIGNAL_NOT_VALIDATED"
        )


    # Layer 32 must not invent thresholds.
    elif (
        not risk[
            "thresholds_validated"
        ]
        or risk[
            "band"
        ]
        == "UNKNOWN"
    ):

        decision = "RECHECK"

        reason_codes.append(
            "VALIDATED_RISK_BAND_UNAVAILABLE"
        )


    elif (
        uncertainty_result[
            "state"
        ]
        == "UNCERTAIN"
    ):

        decision = "RECHECK"

        reason_codes.append(
            "MODEL_UNCERTAIN"
        )


    elif (
        temporal[
            "state"
        ]
        == "RECHECK"
    ):

        decision = "RECHECK"

        reason_codes.append(
            "TEMPORAL_CONFIRMATION_INCOMPLETE"
        )


    elif risk[
        "band"
    ] == "ACTION":

        # A Layer-32 IRRIGATION_REQUEST is only
        # a logical request for the next safety layer.
        #
        # It is NOT a hardware/pump command.
        if (
            temporal[
                "state"
            ]
            == "CONFIRMED_STRESS"
            and forecast_result[
                "status"
            ]
            == "FORECAST_AVAILABLE"
            and forecast_result[
                "validated"
            ]
            and safety[
                "logical_request_allowed"
            ]
        ):

            decision = (
                "IRRIGATION_REQUEST"
            )

            reason_codes.extend(
                [
                    "VALIDATED_ACTION_RISK_BAND",
                    "TEMPORAL_STRESS_CONFIRMED",
                    "VALIDATED_FORECAST_AVAILABLE",
                    "LOGICAL_REQUEST_GATE_PASSED",
                ]
            )


        else:

            # Risk may be high, but missing downstream
            # validation must not silently become an
            # irrigation request.
            decision = "WARNING"

            reason_codes.append(
                "ACTION_LEVEL_RISK_WITH_REQUEST_BLOCK"
            )


            if not forecast_result[
                "validated"
            ]:

                reason_codes.append(
                    "FORECAST_NOT_OPERATIONALLY_VALIDATED"
                )


            if not safety[
                "logical_request_allowed"
            ]:

                reason_codes.append(
                    "SAFETY_STATE_BLOCKS_REQUEST"
                )


    elif risk[
        "band"
    ] == "WARNING":

        decision = "WARNING"

        reason_codes.append(
            "VALIDATED_WARNING_RISK_BAND"
        )


    elif risk[
        "band"
    ] == "MONITOR":

        decision = "MONITOR"

        reason_codes.append(
            "VALIDATED_MONITOR_RISK_BAND"
        )


    elif risk[
        "band"
    ] == "NO_ACTION":

        # A separately validated visual high-stress
        # signal deserves continued observation even
        # when fusion risk remains below monitor band.
        if vision[
            "state"
        ] == "HIGH_STRESS":

            decision = "MONITOR"

            reason_codes.append(
                "VALIDATED_VISION_SIGNAL_MONITOR"
            )

        else:

            decision = "NO_ACTION"

            reason_codes.append(
                "VALIDATED_NO_ACTION_RISK_BAND"
            )


    else:

        raise RuntimeError(
            "Unreachable decision branch."
        )


    if decision not in OUTPUTS:

        raise RuntimeError(
            "Invalid decision output."
        )


    return {
        "decision_version":
            DECISION_VERSION,

        "decision":
            decision,

        "reason_codes":
            reason_codes,

        "inputs_normalized": {
            "vision":
                vision,

            "fusion_risk":
                risk,

            "forecast":
                forecast_result,

            "temporal_consistency":
                temporal,

            "uncertainty":
                uncertainty_result,

            "sensor_validity":
                sensor,

            "safety_state":
                safety,
        },

        "irrigation_request": {
            "created":
                (
                    decision
                    == "IRRIGATION_REQUEST"
                ),

            "logical_ai_request_only":
                True,

            "hardware_command":
                False,

            "dispatch_permitted":
                False,

            "physical_actuation":
                False,
        },

        "scientific_guardrails": {
            "numeric_risk_thresholds_derived_here":
                False,

            "disease_confidence_used_as_water_stress":
                False,

            "unvalidated_forecast_can_create_irrigation_request":
                False,

            "uncertain_input_can_create_irrigation_request":
                False,

            "simulated_sensor_can_create_operational_request":
                False,

            "layer32_authorizes_hardware_dispatch":
                False,

            "physical_action_authorized":
                False,
        },
    }