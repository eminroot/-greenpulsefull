from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping, Optional

import json
import sqlite3


GATEWAY_SCHEMA_VERSION = (
    "greenpulse.ai_gateway_service.v1"
)

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_DATABASE = (
    ROOT / "data/greenpulse.db"
)

DEFAULT_REGISTRY = (
    ROOT / "configs/vision_model_registry_v1.json"
)


@lru_cache(maxsize=1)
def _load_vision_runtime():

    # Model dependency is intentionally isolated
    # inside the AI gateway runtime boundary.
    #
    # Importing src.api or this service module does
    # not instantiate the model.
    from src.vision_inference import (
        GreenPulseVision,
    )

    return GreenPulseVision()


def run_diagnostic_vision(
    *,
    image_path: Any,
    crop: str,
) -> dict[str, Any]:

    runtime = _load_vision_runtime()

    result = runtime.predict(
        image_path=image_path,
        crop=crop,
    )

    if not isinstance(
        result,
        Mapping,
    ):

        raise RuntimeError(
            "Vision runtime returned invalid contract."
        )

    return dict(
        result
    )


def get_model_registry_info(
    registry_path: Optional[Any] = None,
) -> dict[str, Any]:

    path = (
        Path(
            registry_path
        )
        if registry_path
        is not None
        else DEFAULT_REGISTRY
    )

    payload = json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )


    if payload.get(
        "version"
    ) != "1.0":

        raise ValueError(
            "Unsupported model registry version."
        )


    models = payload.get(
        "models"
    )


    if not isinstance(
        models,
        Mapping,
    ):

        raise ValueError(
            "Invalid model registry."
        )


    public_models = {}


    for crop, record in models.items():

        if not isinstance(
            record,
            Mapping,
        ):

            raise ValueError(
                "Invalid model registry record."
            )


        pytorch = record.get(
            "pytorch"
        )

        onnx = record.get(
            "onnx"
        )


        if not isinstance(
            pytorch,
            Mapping,
        ) or not isinstance(
            onnx,
            Mapping,
        ):

            raise ValueError(
                "Model artifact metadata missing."
            )


        public_models[
            str(crop)
        ] = {
            "crop":
                record.get(
                    "crop"
                ),

            "class_count":
                record.get(
                    "class_count"
                ),

            "class_names":
                list(
                    record.get(
                        "class_names",
                        [],
                    )
                ),

            "operational_release_approved":
                bool(
                    record.get(
                        "operational_release_approved",
                        False,
                    )
                ),

            "artifacts": {
                "pytorch_sha256":
                    pytorch.get(
                        "sha256"
                    ),

                "onnx_sha256":
                    onnx.get(
                        "sha256"
                    ),
            },
        }


    return {
        "schema_version":
            GATEWAY_SCHEMA_VERSION,

        "registry_version":
            payload.get(
                "version"
            ),

        "mode":
            payload.get(
                "mode"
            ),

        "crop_identity_source":
            payload.get(
                "crop_identity_source"
            ),

        "unknown_crop_policy":
            payload.get(
                "unknown_crop_policy"
            ),

        "actuation_authorized":
            payload.get(
                "actuation_authorized"
            )
            is True,

        "models":
            public_models,

        "scientific_guardrails": {
            "model_files_loaded":
                False,

            "artifact_paths_exposed":
                False,

            "crop_identity_verified":
                False,

            "operational_release_claimed":
                False,

            "physical_action_authorized":
                False,
        },
    }


def _validate_limit(
    limit: Any,
) -> int:

    if (
        isinstance(
            limit,
            bool,
        )
        or not isinstance(
            limit,
            int,
        )
        or not (
            1 <= limit <= 100
        )
    ):

        raise ValueError(
            "limit must be an integer in [1, 100]."
        )

    return limit


def _read_recent_observations(
    *,
    limit: int,
    database_path: Optional[Any] = None,
    plant_id: Optional[str] = None,
) -> list[dict[str, Any]]:

    limit = _validate_limit(
        limit
    )


    database = (
        Path(
            database_path
        )
        if database_path
        is not None
        else DEFAULT_DATABASE
    )


    if not database.is_file():

        return []


    conn = sqlite3.connect(
        database
    )

    try:

        if plant_id is None:

            rows = conn.execute(
                """
                SELECT response_json
                FROM observations
                ORDER BY rowid DESC
                LIMIT ?
                """,
                (
                    limit,
                ),
            ).fetchall()

        else:

            rows = conn.execute(
                """
                SELECT response_json
                FROM observations
                WHERE plant_id = ?
                ORDER BY rowid DESC
                LIMIT ?
                """,
                (
                    plant_id,
                    limit,
                ),
            ).fetchall()

    finally:

        conn.close()


    result = []


    for row in rows:

        payload = json.loads(
            row[0]
        )

        if not isinstance(
            payload,
            dict,
        ):

            raise ValueError(
                "Stored observation contract invalid."
            )

        result.append(
            payload
        )


    return result


def _extract_decision(
    observation: Mapping[
        str,
        Any,
    ],
) -> tuple[
    Optional[str],
    list[str],
]:

    decision = observation.get(
        "decision"
    )


    if isinstance(
        decision,
        Mapping,
    ):

        action = (
            decision.get(
                "action"
            )
            or decision.get(
                "decision"
            )
        )

        reason_codes = (
            decision.get(
                "reason_codes",
                [],
            )
        )


        if not isinstance(
            reason_codes,
            list,
        ):

            reason_codes = []


        return (
            str(action)
            if action is not None
            else None,

            [
                str(item)
                for item
                in reason_codes
            ],
        )


    final = observation.get(
        "final"
    )


    if isinstance(
        final,
        Mapping,
    ):

        action = final.get(
            "decision"
        )

        reason_codes = final.get(
            "decision_reason_codes",
            [],
        )


        if not isinstance(
            reason_codes,
            list,
        ):

            reason_codes = []


        return (
            str(action)
            if action is not None
            else None,

            [
                str(item)
                for item
                in reason_codes
            ],
        )


    if isinstance(
        decision,
        str,
    ):

        return decision, []


    return None, []


def get_recent_event_view(
    *,
    limit: int = 20,
    database_path: Optional[Any] = None,
) -> dict[str, Any]:

    observations = (
        _read_recent_observations(
            limit=limit,
            database_path=
                database_path,
        )
    )


    events = []


    for observation in observations:

        decision, reasons = (
            _extract_decision(
                observation
            )
        )


        sensor = observation.get(
            "sensor"
        )


        sensor_status = None


        if isinstance(
            sensor,
            Mapping,
        ):

            sensor_status = (
                sensor.get(
                    "status"
                )
            )


        if sensor_status is None:

            stages = observation.get(
                "stages"
            )


            if isinstance(
                stages,
                Mapping,
            ):

                validation = stages.get(
                    "sensor_validation"
                )


                if isinstance(
                    validation,
                    Mapping,
                ):

                    sensor_status = (
                        validation.get(
                            "status"
                        )
                    )


        events.append(
            {
                "event_type":
                    "AI_OBSERVATION",

                "observation_id":
                    observation.get(
                        "observation_id"
                    ),

                "timestamp":
                    observation.get(
                        "timestamp"
                    )
                    or observation.get(
                        "image_captured_at"
                    ),

                "plant_id":
                    observation.get(
                        "plant_id"
                    ),

                "crop":
                    observation.get(
                        "crop"
                    ),

                "decision":
                    decision,

                "reason_codes":
                    reasons,

                "sensor_status":
                    sensor_status,

                "physical_actuation":
                    False,
            }
        )


    return {
        "schema_version":
            GATEWAY_SCHEMA_VERSION,

        "event_source":
            "OBSERVATION_AUDIT_LOG",

        "count":
            len(
                events
            ),

        "events":
            events,

        "physical_actuation":
            False,
    }


def get_recent_sensor_view(
    *,
    limit: int = 20,
    plant_id: Optional[str] = None,
    database_path: Optional[Any] = None,
) -> dict[str, Any]:

    if plant_id is not None:

        if (
            not isinstance(
                plant_id,
                str,
            )
            or not plant_id.strip()
            or len(
                plant_id
            ) > 64
        ):

            raise ValueError(
                "Invalid plant_id."
            )

        plant_id = (
            plant_id.strip()
        )


    observations = (
        _read_recent_observations(
            limit=limit,
            database_path=
                database_path,
            plant_id=
                plant_id,
        )
    )


    snapshots = []


    for observation in observations:

        sensor = observation.get(
            "sensor"
        )


        if isinstance(
            sensor,
            Mapping,
        ):

            snapshots.append(
                {
                    "observation_id":
                        observation.get(
                            "observation_id"
                        ),

                    "timestamp":
                        observation.get(
                            "timestamp"
                        ),

                    "plant_id":
                        observation.get(
                            "plant_id"
                        ),

                    "status":
                        sensor.get(
                            "status"
                        ),

                    "reason":
                        sensor.get(
                            "reason"
                        ),

                    "data":
                        sensor.get(
                            "data"
                        ),

                    "device_authenticated":
                        False,
                }
            )

            continue


        stages = observation.get(
            "stages"
        )


        if isinstance(
            stages,
            Mapping,
        ):

            validation = stages.get(
                "sensor_validation"
            )


            if isinstance(
                validation,
                Mapping,
            ):

                snapshots.append(
                    {
                        "observation_id":
                            observation.get(
                                "observation_id"
                            ),

                        "timestamp":
                            observation.get(
                                "sensor_timestamp"
                            ),

                        "plant_id":
                            observation.get(
                                "plant_id"
                            ),

                        "status":
                            validation.get(
                                "status"
                            ),

                        "reason":
                            validation.get(
                                "reason"
                            ),

                        "data":
                            None,

                        "device_authenticated":
                            False,
                    }
                )


    return {
        "schema_version":
            GATEWAY_SCHEMA_VERSION,

        "sensor_source":
            "OBSERVATION_AUDIT_LOG",

        "plant_id_filter":
            plant_id,

        "count":
            len(
                snapshots
            ),

        "sensors":
            snapshots,

        "scientific_guardrails": {
            "source_field_is_device_authentication":
                False,

            "real_sensor_identity_verified":
                False,

            "sensor_snapshot_is_water_stress_probability":
                False,

            "physical_action_authorized":
                False,
        },
    }


def get_recent_hardware_action_view(
    *,
    limit: int = 20,
    database_path: Optional[Any] = None,
) -> dict[str, Any]:

    from src.hardware_action_audit import (
        get_recent_action_states,
    )

    states = get_recent_action_states(
        limit=limit,
        db_path=database_path,
    )

    return {
        "schema_version":
            "greenpulse.hardware_action_state_collection.v1",

        "source":
            "CANONICAL_HARDWARE_ACTION_STATE_AUDIT",

        "count":
            len(
                states
            ),

        "actions":
            states,

        "real_hardware_ack_validated":
            False,

        "physical_actuation_claimed":
            False,
    }


def get_hardware_action_view(
    command_id: str,
    *,
    database_path: Optional[Any] = None,
) -> Optional[dict[str, Any]]:

    from src.hardware_action_audit import (
        get_action_state_by_command_id,
    )

    result = get_action_state_by_command_id(
        command_id,
        db_path=database_path,
    )

    if result is None:

        return None


    return {
        "schema_version":
            "greenpulse.hardware_action_state_view.v1",

        "source":
            "CANONICAL_HARDWARE_ACTION_STATE_AUDIT",

        "action":
            result,

        "real_hardware_ack_validated":
            False,

        "physical_actuation_claimed":
            False,
    }

