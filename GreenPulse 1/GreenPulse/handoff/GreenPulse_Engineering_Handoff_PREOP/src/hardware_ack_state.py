from __future__ import annotations

from typing import Any, Mapping

from datetime import datetime
from uuid import UUID


SCHEMA_VERSION = (
    "greenpulse.hardware_action_state.v1"
)

VALID_ACTION_STATES = {
    "EXECUTED",
    "REJECTED",
    "FAILED",
    "TIMEOUT",
}

SIMULATED_STATE_MAP = {
    "SIMULATED_EXECUTED":
        "EXECUTED",

    "SIMULATED_REJECTED":
        "REJECTED",

    "SIMULATED_FAILED":
        "FAILED",

    "SIMULATED_TIMEOUT":
        "TIMEOUT",
}


def _uuid_string(
    value: Any,
    name: str,
) -> str:

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
            f"{name} must be a valid UUID."
        ) from exc


def _timestamp(
    value: Any,
) -> str:

    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):

        raise ValueError(
            "timestamp is required."
        )


    try:

        parsed = datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            )
        )

    except ValueError as exc:

        raise ValueError(
            "timestamp must be ISO-8601."
        ) from exc


    if parsed.tzinfo is None:

        raise ValueError(
            "timestamp must include timezone."
        )


    return value


def normalize_simulated_ack(
    ack: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:

    if not isinstance(
        ack,
        Mapping,
    ):

        raise ValueError(
            "ack must be a mapping."
        )


    status = ack.get(
        "status"
    )


    if status not in SIMULATED_STATE_MAP:

        raise ValueError(
            "Unsupported simulated ACK status."
        )


    if (
        ack.get(
            "simulated"
        )
        is not True
    ):

        raise ValueError(
            "Simulated ACK must explicitly set simulated=true."
        )


    if (
        ack.get(
            "physical_actuation"
        )
        is not False
    ):

        raise ValueError(
            "Simulated ACK cannot claim physical actuation."
        )


    if (
        ack.get(
            "real_hardware_ack"
        )
        is not None
    ):

        raise ValueError(
            "Simulated ACK cannot contain real hardware ACK evidence."
        )


    action_state = (
        SIMULATED_STATE_MAP[
            status
        ]
    )


    error_code = ack.get(
        "error_code"
    )


    if (
        action_state
        == "EXECUTED"
    ):

        if error_code is not None:

            raise ValueError(
                "EXECUTED state must not contain an error code."
            )

    else:

        if (
            not isinstance(
                error_code,
                str,
            )
            or not error_code.strip()
        ):

            raise ValueError(
                "Non-executed action state requires error code."
            )


    command_id = _uuid_string(
        ack.get(
            "command_id"
        ),
        "command_id",
    )


    observation_id = _uuid_string(
        ack.get(
            "observation_id"
        ),
        "observation_id",
    )


    plant_id = ack.get(
        "plant_id"
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


    timestamp = _timestamp(
        ack.get(
            "timestamp"
        )
    )


    return {
        "schema_version":
            SCHEMA_VERSION,

        "command_id":
            command_id,

        "observation_id":
            observation_id,

        "plant_id":
            plant_id.strip(),

        "target":
            ack.get(
                "target"
            ),

        "action_state":
            action_state,

        "error_code":
            error_code,

        "state_timestamp":
            timestamp,

        "ack_origin":
            "SIMULATED_TEST_HARNESS",

        "source_status":
            status,

        "simulated":
            True,

        "real_hardware_ack":
            False,

        "real_hardware_ack_validated":
            False,

        "physical_actuation":
            False,

        "backend_surface_allowed":
            True,

        "audit_storage_allowed":
            True,

        "scientific_guardrails": {
            "simulated_executed_means_real_pump_executed":
                False,

            "simulated_ack_is_real_ack_evidence":
                False,

            "real_hardware_transport_validated":
                False,

            "real_hardware_identity_validated":
                False,

            "physical_action_claimed":
                False,
        },
    }


def normalize_real_ack_claim(
    ack: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:

    """
    Future hardware-controller boundary.

    Accepts a structurally shaped real ACK claim but
    does NOT validate transport authenticity, device
    identity, relay state or actual pump actuation.

    Therefore the returned record is explicitly
    UNVERIFIED and cannot serve as operational evidence.
    """

    if not isinstance(
        ack,
        Mapping,
    ):

        raise ValueError(
            "ack must be a mapping."
        )


    state = ack.get(
        "action_state"
    )


    if state not in VALID_ACTION_STATES:

        raise ValueError(
            "Invalid action state."
        )


    command_id = _uuid_string(
        ack.get(
            "command_id"
        ),
        "command_id",
    )


    observation_id = _uuid_string(
        ack.get(
            "observation_id"
        ),
        "observation_id",
    )


    plant_id = ack.get(
        "plant_id"
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


    timestamp = _timestamp(
        ack.get(
            "timestamp"
        )
    )


    error_code = ack.get(
        "error_code"
    )


    if state == "EXECUTED":

        if error_code is not None:

            raise ValueError(
                "EXECUTED state must not contain error code."
            )

    else:

        if (
            not isinstance(
                error_code,
                str,
            )
            or not error_code.strip()
        ):

            raise ValueError(
                "Non-executed action state requires error code."
            )


    return {
        "schema_version":
            SCHEMA_VERSION,

        "command_id":
            command_id,

        "observation_id":
            observation_id,

        "plant_id":
            plant_id.strip(),

        "target":
            ack.get(
                "target"
            ),

        "action_state":
            state,

        "error_code":
            error_code,

        "state_timestamp":
            timestamp,

        "ack_origin":
            "UNVERIFIED_REAL_HARDWARE_CLAIM",

        "source_status":
            state,

        "simulated":
            False,

        "real_hardware_ack":
            True,

        "real_hardware_ack_validated":
            False,

        "physical_actuation":
            None,

        "backend_surface_allowed":
            True,

        "audit_storage_allowed":
            True,

        "scientific_guardrails": {
            "real_ack_claim_is_verified_hardware_evidence":
                False,

            "real_hardware_transport_validated":
                False,

            "real_hardware_identity_validated":
                False,

            "relay_state_verified":
                False,

            "pump_state_verified":
                False,

            "physical_action_claimed":
                False,
        },
    }


def validate_request_ack_linkage(
    *,
    actuator_request: Mapping[
        str,
        Any,
    ],
    action_state: Mapping[
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
        action_state,
        Mapping,
    ):

        raise ValueError(
            "action_state must be a mapping."
        )


    request_command_id = (
        actuator_request.get(
            "command_id"
        )
    )

    state_command_id = (
        action_state.get(
            "command_id"
        )
    )


    linked = (
        isinstance(
            request_command_id,
            str,
        )
        and isinstance(
            state_command_id,
            str,
        )
        and request_command_id
        == state_command_id
    )


    return {
        "linked":
            linked,

        "command_id":
            request_command_id,

        "reason":
            (
                "COMMAND_ID_MATCH"
                if linked
                else "COMMAND_ID_MISMATCH"
            ),

        "real_hardware_ack_validated":
            False,
    }