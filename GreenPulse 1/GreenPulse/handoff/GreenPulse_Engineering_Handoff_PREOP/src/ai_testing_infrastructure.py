from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import json
import sqlite3

from src.audit_traceability import (
    trace_command,
)

from src.data_logging_writer import (
    write_audit_bundle,
)


SCHEMA_VERSION = (
    "greenpulse.ai_testing_infrastructure.v1"
)

REFERENCE_FIXTURE_VERSION = (
    "greenpulse.layer49.reference_input.v1"
)


STAGE_ORDER = (
    "image",
    "yolo",
    "fusion",
    "risk",
    "forecast",
    "decision",
    "api",
    "database",
    "simulated_hardware",
)


EXPECTED_REFERENCE_BEHAVIOR = {
    "vision": {
        "predicted_class":
            "healthy",

        "confidence":
            0.99,

        "execution_mode":
            "DETERMINISTIC_TEST_DOUBLE",

        "model_family":
            "YOLO11N_CLASSIFICATION_INTERFACE",

        "real_model_inference":
            False,
    },

    "fusion": {
        "risk_signal":
            0.25,

        "execution_mode":
            "DETERMINISTIC_TEST_DOUBLE",

        "real_trained_fusion_model":
            False,
    },

    "risk": {
        "risk_score":
            25.0,

        "execution_mode":
            "DETERMINISTIC_TEST_DOUBLE",
    },

    "forecast": {
        "trend":
            "STABLE",

        "forecast_risk":
            25.0,

        "execution_mode":
            "DETERMINISTIC_TEST_DOUBLE",

        "real_forecast_validation":
            False,
    },

    "decision": {
        "decision":
            "MONITOR",

        "execution_mode":
            "DETERMINISTIC_TEST_DOUBLE",

        "physical_dispatch_permitted":
            False,
    },

    "api": {
        "schema_version":
            "greenpulse.layer49.test_api.v1",

        "decision":
            "MONITOR",

        "command_id":
            "L49-CMD-001",
    },

    "hardware": {
        "status":
            "SIMULATED_ACK",

        "physical_actuation":
            False,

        "execution_mode":
            "DETERMINISTIC_SIMULATED_HARDWARE",
    },
}


def load_reference_fixture(
    path: Any,
) -> dict[str, Any]:

    payload = json.loads(
        Path(
            path
        ).read_text(
            encoding="utf-8-sig"
        )
    )


    if (
        payload.get(
            "schema_version"
        )
        != REFERENCE_FIXTURE_VERSION
    ):

        raise ValueError(
            "Unsupported Layer 49 reference fixture."
        )


    sensor = payload.get(
        "sensor"
    )


    if not isinstance(
        sensor,
        Mapping,
    ):

        raise ValueError(
            "Reference sensor missing."
        )


    if (
        sensor.get(
            "source"
        )
        != "SIMULATED"
    ):

        raise ValueError(
            "Layer 49 reference sensor must be SIMULATED."
        )


    image = payload.get(
        "image"
    )


    if not isinstance(
        image,
        Mapping,
    ):

        raise ValueError(
            "Reference image descriptor missing."
        )


    return deepcopy(
        payload
    )


def _reference_vision_stage(
    image: Mapping[str, Any],
) -> dict[str, Any]:

    if not image.get(
        "image_id"
    ):

        raise ValueError(
            "image_id required."
        )


    return deepcopy(
        EXPECTED_REFERENCE_BEHAVIOR[
            "vision"
        ]
    )


def _reference_fusion_stage(
    vision: Mapping[str, Any],
    sensor: Mapping[str, Any],
) -> dict[str, Any]:

    if (
        sensor.get(
            "source"
        )
        != "SIMULATED"
    ):

        raise ValueError(
            "Reference fusion requires simulated sensor."
        )


    if not vision.get(
        "predicted_class"
    ):

        raise ValueError(
            "Vision prediction missing."
        )


    return deepcopy(
        EXPECTED_REFERENCE_BEHAVIOR[
            "fusion"
        ]
    )


def _reference_risk_stage(
    fusion: Mapping[str, Any],
) -> dict[str, Any]:

    if fusion.get(
        "risk_signal"
    ) is None:

        raise ValueError(
            "Fusion risk signal missing."
        )


    return deepcopy(
        EXPECTED_REFERENCE_BEHAVIOR[
            "risk"
        ]
    )


def _reference_forecast_stage(
    risk: Mapping[str, Any],
) -> dict[str, Any]:

    if risk.get(
        "risk_score"
    ) is None:

        raise ValueError(
            "Risk score missing."
        )


    return deepcopy(
        EXPECTED_REFERENCE_BEHAVIOR[
            "forecast"
        ]
    )


def _reference_decision_stage(
    risk: Mapping[str, Any],
    forecast: Mapping[str, Any],
) -> dict[str, Any]:

    if (
        risk.get(
            "risk_score"
        )
        is None
        or forecast.get(
            "forecast_risk"
        )
        is None
    ):

        raise ValueError(
            "Decision inputs incomplete."
        )


    return deepcopy(
        EXPECTED_REFERENCE_BEHAVIOR[
            "decision"
        ]
    )


def _reference_api_stage(
    decision: Mapping[str, Any],
) -> dict[str, Any]:

    if not decision.get(
        "decision"
    ):

        raise ValueError(
            "Decision missing."
        )


    return deepcopy(
        EXPECTED_REFERENCE_BEHAVIOR[
            "api"
        ]
    )


def _reference_hardware_stage(
    api_output: Mapping[str, Any],
) -> dict[str, Any]:

    if not api_output.get(
        "command_id"
    ):

        raise ValueError(
            "command_id missing."
        )


    return deepcopy(
        EXPECTED_REFERENCE_BEHAVIOR[
            "hardware"
        ]
    )


def _build_audit_bundle(
    *,
    reference: Mapping[str, Any],
    behavior: Mapping[str, Any],
) -> dict[str, Any]:

    image = reference[
        "image"
    ]

    sensor = reference[
        "sensor"
    ]

    vision = behavior[
        "vision"
    ]

    risk = behavior[
        "risk"
    ]

    forecast = behavior[
        "forecast"
    ]

    decision = behavior[
        "decision"
    ]

    api_output = behavior[
        "api"
    ]


    observation_id = "L49-OBS-001"
    model_version_id = "L49-YOLO-TEST-DOUBLE-V1"
    risk_id = "L49-RISK-001"
    forecast_id = "L49-FORECAST-001"
    decision_id = "L49-DECISION-001"
    command_id = api_output[
        "command_id"
    ]


    timestamp = (
        "2026-01-01T00:00:00Z"
    )


    return {
        "observation": {
            "observation_id":
                observation_id,

            "timestamp":
                timestamp,

            "plant_id":
                "L49-PLANT-001",

            "crop":
                "tomato",
        },

        "model_versions": [
            {
                "model_version_id":
                    model_version_id,

                "model_name":
                    "YOLO11n Classification Interface Test Double",

                "model_sha256":
                    None,

                "artifact_path":
                    None,

                "created_at":
                    timestamp,
            }
        ],

        "images": [
            {
                "image_id":
                    image[
                        "image_id"
                    ],

                "observation_id":
                    observation_id,

                "image_path":
                    image[
                        "image_path"
                    ],

                "image_sha256":
                    image.get(
                        "image_sha256"
                    ),

                "captured_at":
                    timestamp,
            }
        ],

        "predictions": [
            {
                "prediction_id":
                    "L49-PRED-001",

                "observation_id":
                    observation_id,

                "image_id":
                    image[
                        "image_id"
                    ],

                "model_version_id":
                    model_version_id,

                "predicted_class":
                    vision[
                        "predicted_class"
                    ],

                "confidence":
                    vision[
                        "confidence"
                    ],

                "created_at":
                    timestamp,
            }
        ],

        "sensor_readings": [
            {
                "sensor_reading_id":
                    sensor[
                        "sensor_reading_id"
                    ],

                "observation_id":
                    observation_id,

                "sensor_id":
                    sensor[
                        "sensor_id"
                    ],

                "sensor_type":
                    sensor[
                        "sensor_type"
                    ],

                "value":
                    sensor[
                        "value"
                    ],

                "unit":
                    sensor[
                        "unit"
                    ],

                "timestamp":
                    timestamp,

                "validation_status":
                    sensor[
                        "validation_status"
                    ],
            }
        ],

        "risk_scores": [
            {
                "risk_score_id":
                    risk_id,

                "observation_id":
                    observation_id,

                "model_version_id":
                    model_version_id,

                "risk_score":
                    risk[
                        "risk_score"
                    ],

                "created_at":
                    timestamp,
            }
        ],

        "forecasts": [
            {
                "forecast_id":
                    forecast_id,

                "observation_id":
                    observation_id,

                "model_version_id":
                    model_version_id,

                "forecast_json":
                    json.dumps(
                        {
                            "trend":
                                forecast[
                                    "trend"
                                ],

                            "forecast_risk":
                                forecast[
                                    "forecast_risk"
                                ],
                        },
                        sort_keys=True,
                    ),

                "created_at":
                    timestamp,
            }
        ],

        "decision": {
            "decision_id":
                decision_id,

            "observation_id":
                observation_id,

            "risk_score_id":
                risk_id,

            "forecast_id":
                forecast_id,

            "decision":
                decision[
                    "decision"
                ],

            "reason_json":
                json.dumps(
                    [
                        "LAYER49_REFERENCE_TEST"
                    ]
                ),

            "created_at":
                timestamp,
        },

        "command": {
            "command_id":
                command_id,

            "observation_id":
                observation_id,

            "decision_id":
                decision_id,

            "command_type":
                "MONITOR_ONLY",

            "payload_json":
                json.dumps(
                    {
                        "physical_dispatch_permitted":
                            False
                    },
                    sort_keys=True,
                ),

            "created_at":
                timestamp,
        },

        "actions": [
            {
                "action_id":
                    "L49-ACTION-001",

                "command_id":
                    command_id,

                "action_state":
                    "SIMULATED",

                "ack_type":
                    "SIMULATED_ACK",

                "created_at":
                    timestamp,
            }
        ],

        "sustainability_metrics": [
            {
                "metric_id":
                    "L49-METRIC-001",

                "observation_id":
                    observation_id,

                "command_id":
                    command_id,

                "metric_name":
                    "REFERENCE_TEST_ONLY",

                "metric_value":
                    0.0,

                "metric_unit":
                    "test",

                "created_at":
                    timestamp,
            }
        ],

        "system_events": [
            {
                "event_id":
                    "L49-EVENT-001",

                "observation_id":
                    observation_id,

                "command_id":
                    command_id,

                "event_type":
                    "LAYER49_REFERENCE_E2E",

                "severity":
                    "INFO",

                "payload_json":
                    json.dumps(
                        {
                            "real_model_inference":
                                False,

                            "physical_actuation":
                                False,
                        },
                        sort_keys=True,
                    ),

                "created_at":
                    timestamp,
            }
        ],
    }


def run_reference_e2e(
    conn: sqlite3.Connection,
    reference_input: Mapping[str, Any],
) -> dict[str, Any]:

    if not isinstance(
        conn,
        sqlite3.Connection,
    ):

        raise ValueError(
            "conn must be sqlite3.Connection."
        )


    original = deepcopy(
        reference_input
    )

    reference = deepcopy(
        reference_input
    )


    if (
        reference.get(
            "schema_version"
        )
        != REFERENCE_FIXTURE_VERSION
    ):

        raise ValueError(
            "Reference fixture version mismatch."
        )


    if (
        reference[
            "sensor"
        ].get(
            "source"
        )
        != "SIMULATED"
    ):

        raise ValueError(
            "Only simulated sensor input is allowed."
        )


    vision = _reference_vision_stage(
        reference[
            "image"
        ]
    )

    fusion = _reference_fusion_stage(
        vision,
        reference[
            "sensor"
        ],
    )

    risk = _reference_risk_stage(
        fusion
    )

    forecast = _reference_forecast_stage(
        risk
    )

    decision = _reference_decision_stage(
        risk,
        forecast,
    )

    api_output = _reference_api_stage(
        decision
    )


    behavior = {
        "vision":
            vision,

        "fusion":
            fusion,

        "risk":
            risk,

        "forecast":
            forecast,

        "decision":
            decision,

        "api":
            api_output,
    }


    bundle = _build_audit_bundle(
        reference=reference,
        behavior=behavior,
    )


    write_result = write_audit_bundle(
        conn,
        bundle,
    )


    trace = trace_command(
        conn,
        api_output[
            "command_id"
        ],
    )


    hardware = _reference_hardware_stage(
        api_output
    )


    behavior[
        "hardware"
    ] = hardware


    if reference_input != original:

        raise RuntimeError(
            "Reference input mutated."
        )


    return {
        "schema_version":
            SCHEMA_VERSION,

        "fixture_version":
            REFERENCE_FIXTURE_VERSION,

        "stage_order":
            list(
                STAGE_ORDER
            ),

        "behavior":
            behavior,

        "database": {
            "write":
                write_result,

            "required_lineage_complete":
                trace[
                    "required_lineage_complete"
                ],
        },

        "execution_boundary": {
            "real_yolo_inference":
                False,

            "real_trained_fusion_execution":
                False,

            "real_forecast_validation":
                False,

            "real_hardware_actuation":
                False,

            "database_backend":
                "CALLER_SUPPLIED_SQLITE",
        },
    }