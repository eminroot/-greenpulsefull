from __future__ import annotations

from typing import Any, Mapping, Optional
from uuid import UUID, uuid4

import math


SCHEMA_VERSION = (
    "greenpulse.standard_actuator_request.v1"
)

CONTRACT_VERSION = "1.0.0"

TARGET = "MAIN_IRRIGATION_PUMP"

ALLOWED_ACTION = "IRRIGATION_REQUEST"

OPERATIONAL_CONFIDENCE_SOURCE = (
    "CALIBRATED_MULTIMODAL_FUSION"
)


def _finite_number(
    value: Any,
    name: str,
) -> float:

    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            (int, float),
        )
    ):

        raise ValueError(
            f"{name} must be numeric."
        )

    result = float(
        value
    )

    if not math.isfinite(
        result
    ):

        raise ValueError(
            f"{name} must be finite."
        )

    return result


def _uuid_string(
    value: Optional[Any],
) -> str:

    if value is None:

        return str(
            uuid4()
        )

    try:

        return str(
            UUID(
                str(
                    value
                )
            )
        )

    except (
        ValueError,
        TypeError,
        AttributeError,
    ) as exc:

        raise ValueError(
            "command_id must be a valid UUID."
        ) from exc


def _blocked(
    *,
    standard_output: Mapping[
        str,
        Any,
    ],
    reason_codes: list[str],
) -> dict[str, Any]:

    return {
        "schema_version":
            SCHEMA_VERSION,

        "contract_version":
            CONTRACT_VERSION,

        "status":
            "BLOCKED",

        "observation_id":
            standard_output.get(
                "observation_id"
            ),

        "plant_id":
            standard_output.get(
                "plant_id"
            ),

        "actuator_request":
            None,

        "hardware_safety_check_required":
            True,

        "hardware_dispatch_permitted":
            False,

        "physical_actuation_authorized":
            False,

        "reason_codes":
            list(
                dict.fromkeys(
                    str(item)
                    for item
                    in reason_codes
                )
            ),
    }


def build_standard_actuator_request(
    *,
    standard_output: Mapping[
        str,
        Any,
    ],
    safety_result: Mapping[
        str,
        Any,
    ],
    requested_duration_seconds: Any,
    decision_confidence: Any,
    confidence_source: str,
    command_id: Optional[Any] = None,
    test_only: bool = False,
) -> dict[str, Any]:

    if not isinstance(
        standard_output,
        Mapping,
    ):

        raise ValueError(
            "standard_output must be a mapping."
        )


    if (
        standard_output.get(
            "schema_version"
        )
        != "greenpulse.standard_ai_output.v1"
    ):

        raise ValueError(
            "Unsupported standard AI output schema."
        )


    if not isinstance(
        safety_result,
        Mapping,
    ):

        raise ValueError(
            "safety_result must be a mapping."
        )


    if not isinstance(
        test_only,
        bool,
    ):

        raise ValueError(
            "test_only must be bool."
        )


    observation_id = (
        standard_output.get(
            "observation_id"
        )
    )

    plant_id = (
        standard_output.get(
            "plant_id"
        )
    )


    if (
        not isinstance(
            observation_id,
            str,
        )
        or not observation_id.strip()
    ):

        raise ValueError(
            "observation_id is required."
        )


    if (
        not isinstance(
            plant_id,
            str,
        )
        or not plant_id.strip()
    ):

        raise ValueError(
            "plant_id is required."
        )


    decision = (
        standard_output.get(
            "decision"
        )
    )


    if decision != ALLOWED_ACTION:

        raise ValueError(
            "Only IRRIGATION_REQUEST can create "
            "an actuator request."
        )


    reasons = (
        standard_output.get(
            "reason_codes"
        )
    )


    if not isinstance(
        reasons,
        list,
    ):

        raise ValueError(
            "reason_codes must be a list."
        )


    risk = (
        standard_output.get(
            "risk"
        )
    )


    if not isinstance(
        risk,
        Mapping,
    ):

        raise ValueError(
            "Operational risk object is required."
        )


    risk_score = _finite_number(
        risk.get(
            "stress_risk_score"
        ),
        "stress_risk_score",
    )


    if not (
        0.0
        <= risk_score
        <= 100.0
    ):

        raise ValueError(
            "stress_risk_score must be in [0, 100]."
        )


    confidence = _finite_number(
        decision_confidence,
        "decision_confidence",
    )


    if not (
        0.0
        <= confidence
        <= 1.0
    ):

        raise ValueError(
            "decision_confidence must be in [0, 1]."
        )


    if (
        not isinstance(
            confidence_source,
            str,
        )
        or not confidence_source.strip()
    ):

        raise ValueError(
            "confidence_source is required."
        )


    confidence_source = (
        confidence_source.strip()
    )


    duration = _finite_number(
        requested_duration_seconds,
        "requested_duration_seconds",
    )


    if duration <= 0.0:

        raise ValueError(
            "requested_duration_seconds must be > 0."
        )


    model_versions = (
        standard_output.get(
            "model_versions"
        )
    )


    if not isinstance(
        model_versions,
        Mapping,
    ):

        raise ValueError(
            "model_versions mapping is required."
        )


    decision_version = (
        model_versions.get(
            "decision"
        )
    )


    if (
        not isinstance(
            decision_version,
            str,
        )
        or not decision_version.strip()
    ):

        raise ValueError(
            "decision version is required."
        )


    request_allowed = (
        safety_result.get(
            "request_allowed_by_safety_policy"
        )
        is True
    )


    if not request_allowed:

        raise ValueError(
            "Decision safety policy did not allow request."
        )


    if (
        safety_result.get(
            "hardware_dispatch_permitted"
        )
        is True
    ):

        raise ValueError(
            "AI safety layer must not directly "
            "permit hardware dispatch."
        )


    if (
        safety_result.get(
            "physical_actuation_authorized"
        )
        is True
    ):

        raise ValueError(
            "AI safety layer must not authorize "
            "physical actuation."
        )


    policy_status = (
        safety_result.get(
            "policy_status"
        )
    )


    if not test_only:

        if (
            policy_status
            != "OPERATIONAL_VALIDATED"
        ):

            raise ValueError(
                "Operational request requires "
                "OPERATIONAL_VALIDATED safety policy."
            )


        if (
            confidence_source
            != OPERATIONAL_CONFIDENCE_SOURCE
        ):

            raise ValueError(
                "Operational request confidence must "
                "come from calibrated multimodal fusion."
            )


    policy_version = (
        safety_result.get(
            "policy_version"
        )
    )


    if (
        not isinstance(
            policy_version,
            str,
        )
        or not policy_version.strip()
    ):

        raise ValueError(
            "safety policy version is required."
        )


    request = {
        "schema_version":
            SCHEMA_VERSION,

        "contract_version":
            CONTRACT_VERSION,

        "command_id":
            _uuid_string(
                command_id
            ),

        "observation_id":
            observation_id,

        "plant_id":
            plant_id,

        "action":
            ALLOWED_ACTION,

        "target":
            TARGET,

        "risk_score":
            risk_score,

        "confidence":
            confidence,

        "confidence_source":
            confidence_source,

        "requested_duration_seconds":
            duration,

        "reason_codes":
            [
                str(
                    item
                )
                for item
                in reasons
            ],

        "decision_version":
            decision_version.strip(),

        "safety_policy_version":
            policy_version.strip(),

        "mode":
            (
                "TEST_ONLY"
                if test_only
                else "OPERATIONAL_REQUEST"
            ),

        "test_only":
            test_only,

        "hardware_safety_check_required":
            True,

        "direct_electrical_control":
            False,

        "relay_or_mosfet_controlled_by_ai":
            False,

        "hardware_dispatch_permitted_by_ai":
            False,

        "physical_actuation_authorized_by_ai":
            False,
    }


    return request


def prepare_actuator_handoff(
    *,
    standard_output: Mapping[
        str,
        Any,
    ],
    safety_result: Mapping[
        str,
        Any,
    ],
    requested_duration_seconds: Optional[Any] = None,
    decision_confidence: Optional[Any] = None,
    confidence_source: Optional[str] = None,
    command_id: Optional[Any] = None,
    test_only: bool = False,
) -> dict[str, Any]:

    if not isinstance(
        standard_output,
        Mapping,
    ):

        raise ValueError(
            "standard_output must be a mapping."
        )


    blocking_reasons = []


    if (
        standard_output.get(
            "decision"
        )
        != ALLOWED_ACTION
    ):

        blocking_reasons.append(
            "DECISION_IS_NOT_IRRIGATION_REQUEST"
        )


    risk = standard_output.get(
        "risk"
    )


    if (
        not isinstance(
            risk,
            Mapping,
        )
        or risk.get(
            "stress_risk_score"
        )
        is None
    ):

        blocking_reasons.append(
            "VALIDATED_RISK_SCORE_UNAVAILABLE"
        )


    if not isinstance(
        safety_result,
        Mapping,
    ):

        blocking_reasons.append(
            "DECISION_SAFETY_RESULT_UNAVAILABLE"
        )

    elif (
        safety_result.get(
            "request_allowed_by_safety_policy"
        )
        is not True
    ):

        blocking_reasons.append(
            "SAFETY_POLICY_DID_NOT_ALLOW_REQUEST"
        )


    if requested_duration_seconds is None:

        blocking_reasons.append(
            "REQUEST_DURATION_UNAVAILABLE"
        )


    if decision_confidence is None:

        blocking_reasons.append(
            "DECISION_CONFIDENCE_UNAVAILABLE"
        )


    if (
        not isinstance(
            confidence_source,
            str,
        )
        or not confidence_source.strip()
    ):

        blocking_reasons.append(
            "CONFIDENCE_SOURCE_UNAVAILABLE"
        )


    if blocking_reasons:

        return _blocked(
            standard_output=
                standard_output,

            reason_codes=
                blocking_reasons,
        )


    try:

        request = (
            build_standard_actuator_request(
                standard_output=
                    standard_output,

                safety_result=
                    safety_result,

                requested_duration_seconds=
                    requested_duration_seconds,

                decision_confidence=
                    decision_confidence,

                confidence_source=
                    confidence_source,

                command_id=
                    command_id,

                test_only=
                    test_only,
            )
        )

    except ValueError as exc:

        return _blocked(
            standard_output=
                standard_output,

            reason_codes=[
                "ACTUATOR_REQUEST_VALIDATION_FAILED",
                str(
                    exc
                ),
            ],
        )


    return {
        "schema_version":
            SCHEMA_VERSION,

        "contract_version":
            CONTRACT_VERSION,

        "status":
            (
                "TEST_REQUEST_CREATED"
                if test_only
                else "ACTUATOR_REQUEST_CREATED"
            ),

        "observation_id":
            standard_output.get(
                "observation_id"
            ),

        "plant_id":
            standard_output.get(
                "plant_id"
            ),

        "actuator_request":
            request,

        "hardware_safety_check_required":
            True,

        "hardware_dispatch_permitted":
            False,

        "physical_actuation_authorized":
            False,

        "reason_codes": [
            (
                "SYNTHETIC_TEST_REQUEST_ONLY"
                if test_only
                else
                "STANDARD_ACTUATOR_REQUEST_CREATED"
            )
        ],
    }


def validate_ack_linkage(
    *,
    actuator_request: Mapping[
        str,
        Any,
    ],
    hardware_ack: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:

    if not isinstance(
        actuator_request,
        Mapping,
    ):

        raise ValueError(
            "actuator_request must be a mapping."
        )


    if not isinstance(
        hardware_ack,
        Mapping,
    ):

        raise ValueError(
            "hardware_ack must be a mapping."
        )


    request_id = (
        actuator_request.get(
            "command_id"
        )
    )

    ack_id = (
        hardware_ack.get(
            "command_id"
        )
    )


    if (
        not isinstance(
            request_id,
            str,
        )
        or not request_id
    ):

        raise ValueError(
            "Actuator request command_id missing."
        )


    if (
        not isinstance(
            ack_id,
            str,
        )
        or not ack_id
    ):

        return {
            "linked":
                False,

            "command_id":
                request_id,

            "reason":
                "ACK_COMMAND_ID_MISSING",

            "real_hardware_ack_validated":
                False,
        }


    linked = (
        ack_id
        == request_id
    )


    return {
        "linked":
            linked,

        "command_id":
            request_id,

        "reason":
            (
                "COMMAND_ID_MATCH"
                if linked
                else "COMMAND_ID_MISMATCH"
            ),

        # Layer 38 checks linkage only.
        # Real ACK state semantics belong to Layer 39.
        "real_hardware_ack_validated":
            False,
    }