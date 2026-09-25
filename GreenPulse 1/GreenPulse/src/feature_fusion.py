from __future__ import annotations

from typing import Any, Mapping, Optional

import math
import numpy as np

from src.vision_only_baseline import (
    MODEL_FEATURE_NAMES as VISION_MODEL_FEATURE_NAMES,
    extract_model_vector as extract_vision_model_vector,
)

from src.sensor_only_baseline import (
    MODEL_FEATURE_NAMES as SENSOR_MODEL_FEATURE_NAMES,
)


SCHEMA_VERSION = "greenpulse.multimodal_feature_fusion.v1"

FEATURE_VECTOR_VERSION = "multimodal_feature_vector_v1"

EXPECTED_SENSOR_FEATURE_VECTOR_VERSION = (
    "sensor_feature_vector_v1"
)

EXPECTED_TEMPORAL_FEATURE_VECTOR_VERSION = (
    "temporal_feature_vector_v1"
)


TEMPORAL_FEATURE_NAMES = [
    "risk_trend_code",
    "risk_velocity",
    "risk_acceleration",
    "temporal_consistency_code",
]


FUSION_FEATURE_NAMES = (
    [
        "vision__" + name
        for name in VISION_MODEL_FEATURE_NAMES
    ]
    +
    [
        "sensor__" + name
        for name in SENSOR_MODEL_FEATURE_NAMES
    ]
    +
    [
        "temporal__" + name
        for name in TEMPORAL_FEATURE_NAMES
    ]
    +
    [
        "temporal__available"
    ]
)


def _finite_float(
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


def _extract_sensor_vector(
    sensor_features: Mapping[
        str,
        Any,
    ],
) -> np.ndarray:

    if (
        sensor_features.get(
            "feature_vector_version"
        )
        != EXPECTED_SENSOR_FEATURE_VECTOR_VERSION
    ):
        raise ValueError(
            "Unsupported sensor feature-vector version."
        )

    vector = sensor_features.get(
        "feature_vector"
    )

    if not isinstance(
        vector,
        Mapping,
    ):
        raise ValueError(
            "Missing sensor feature_vector."
        )

    names = vector.get(
        "names"
    )

    raw_values = vector.get(
        "raw_values"
    )

    if not isinstance(
        names,
        list,
    ) or not isinstance(
        raw_values,
        list,
    ):
        raise ValueError(
            "Sensor feature names/raw_values missing."
        )

    if len(
        names
    ) != len(
        raw_values
    ):
        raise ValueError(
            "Sensor feature name/value length mismatch."
        )

    mapping = dict(
        zip(
            names,
            raw_values,
        )
    )

    missing = [
        name
        for name in SENSOR_MODEL_FEATURE_NAMES
        if name not in mapping
    ]

    if missing:

        raise ValueError(
            "Required sensor fusion features missing: "
            + ", ".join(
                missing
            )
        )

    values = np.asarray(
        [
            _finite_float(
                mapping[
                    name
                ],
                name,
            )
            for name in SENSOR_MODEL_FEATURE_NAMES
        ],
        dtype=np.float64,
    )

    if values.shape != (
        len(
            SENSOR_MODEL_FEATURE_NAMES
        ),
    ):

        raise RuntimeError(
            "Sensor fusion vector shape mismatch."
        )

    return values


def _extract_temporal_vector(
    temporal_features: Optional[
        Mapping[str, Any]
    ],
) -> tuple[
    np.ndarray,
    bool,
]:

    if temporal_features is None:

        return (
            np.zeros(
                len(
                    TEMPORAL_FEATURE_NAMES
                ),
                dtype=np.float64,
            ),
            False,
        )

    if (
        temporal_features.get(
            "feature_vector_version"
        )
        != EXPECTED_TEMPORAL_FEATURE_VECTOR_VERSION
    ):

        raise ValueError(
            "Unsupported temporal feature-vector version."
        )

    vector = temporal_features.get(
        "feature_vector"
    )

    if not isinstance(
        vector,
        Mapping,
    ):

        raise ValueError(
            "Missing temporal feature_vector."
        )

    names = vector.get(
        "names"
    )

    values = vector.get(
        "values"
    )

    if not isinstance(
        names,
        list,
    ) or not isinstance(
        values,
        list,
    ):

        raise ValueError(
            "Temporal feature names/values missing."
        )

    if len(
        names
    ) != len(
        values
    ):

        raise ValueError(
            "Temporal feature name/value length mismatch."
        )

    mapping = dict(
        zip(
            names,
            values,
        )
    )

    missing = [
        name
        for name in TEMPORAL_FEATURE_NAMES
        if name not in mapping
    ]

    if missing:

        raise ValueError(
            "Required temporal fusion features missing: "
            + ", ".join(
                missing
            )
        )

    result = np.asarray(
        [
            _finite_float(
                mapping[
                    name
                ],
                name,
            )
            for name in TEMPORAL_FEATURE_NAMES
        ],
        dtype=np.float64,
    )

    return (
        result,
        True,
    )


def _validate_identity(
    sensor_features: Mapping[
        str,
        Any,
    ],
    plant_delta: Optional[
        Mapping[str, Any]
    ],
) -> None:

    if plant_delta is None:
        return

    identity = plant_delta.get(
        "identity"
    )

    if not isinstance(
        identity,
        Mapping,
    ):
        raise ValueError(
            "Plant delta identity missing."
        )

    if (
        identity.get(
            "type"
        )
        != "PLANT"
    ):
        return

    sensor_plant_id = sensor_features.get(
        "plant_id"
    )

    if (
        identity.get(
            "id"
        )
        != sensor_plant_id
    ):

        raise ValueError(
            "PLANT_ID_MISMATCH"
        )


def build_multimodal_feature_vector(
    *,
    visual_features: Mapping[
        str,
        Any,
    ],
    sensor_features: Mapping[
        str,
        Any,
    ],
    plant_delta: Optional[
        Mapping[str, Any]
    ] = None,
    temporal_features: Optional[
        Mapping[str, Any]
    ] = None,
    time_sync_status: str,
) -> dict[str, Any]:

    if time_sync_status != "SYNCED":

        raise ValueError(
            "Multimodal fusion requires "
            "time_sync_status='SYNCED'."
        )

    if not isinstance(
        visual_features,
        Mapping,
    ):

        raise TypeError(
            "visual_features must be a mapping."
        )

    if not isinstance(
        sensor_features,
        Mapping,
    ):

        raise TypeError(
            "sensor_features must be a mapping."
        )

    _validate_identity(
        sensor_features,
        plant_delta,
    )

    vision_vector = extract_vision_model_vector(
        visual_features,
        plant_delta,
    )

    sensor_vector = _extract_sensor_vector(
        sensor_features
    )

    (
        temporal_vector,
        temporal_available,
    ) = _extract_temporal_vector(
        temporal_features
    )

    fused = np.concatenate(
        [
            vision_vector,
            sensor_vector,
            temporal_vector,
            np.asarray(
                [
                    float(
                        temporal_available
                    )
                ],
                dtype=np.float64,
            ),
        ]
    )

    if fused.shape != (
        len(
            FUSION_FEATURE_NAMES
        ),
    ):

        raise RuntimeError(
            "Multimodal feature-vector schema mismatch."
        )

    if not np.all(
        np.isfinite(
            fused
        )
    ):

        raise ValueError(
            "Multimodal feature vector contains "
            "non-finite values."
        )

    return {
        "schema_version":
            SCHEMA_VERSION,

        "feature_vector_version":
            FEATURE_VECTOR_VERSION,

        "plant_id":
            sensor_features.get(
                "plant_id"
            ),

        "timestamp":
            sensor_features.get(
                "timestamp"
            ),

        "time_sync_status":
            time_sync_status,

        "modalities": {
            "vision":
                True,

            "sensor":
                True,

            "plant_delta":
                plant_delta
                is not None,

            "temporal":
                temporal_available,
        },

        "feature_groups": {
            "vision_feature_count":
                len(
                    VISION_MODEL_FEATURE_NAMES
                ),

            "sensor_feature_count":
                len(
                    SENSOR_MODEL_FEATURE_NAMES
                ),

            "temporal_feature_count":
                len(
                    TEMPORAL_FEATURE_NAMES
                ),

            "availability_feature_count":
                1,
        },

        "feature_vector": {
            "names":
                list(
                    FUSION_FEATURE_NAMES
                ),

            "values":
                [
                    float(
                        value
                    )
                    for value in fused
                ],

            "length":
                len(
                    FUSION_FEATURE_NAMES
                ),

            "ordering":
                (
                    "VISION_THEN_SENSOR_THEN_"
                    "TEMPORAL_THEN_AVAILABILITY"
                ),

            "normalization_applied":
                False,

            "normalization_policy":
                (
                    "Fusion model owns train-only scaling. "
                    "Layer 22 never fits scaling on runtime "
                    "or evaluation data."
                ),
        },

        "provenance": {
            "vision_feature_vector_version":
                visual_features.get(
                    "feature_vector_version"
                ),

            "sensor_feature_vector_version":
                sensor_features.get(
                    "feature_vector_version"
                ),

            "plant_delta_schema_version":
                (
                    plant_delta.get(
                        "schema_version"
                    )
                    if plant_delta
                    is not None
                    else None
                ),

            "temporal_feature_vector_version":
                (
                    temporal_features.get(
                        "feature_vector_version"
                    )
                    if temporal_features
                    is not None
                    else None
                ),
        },

        "scientific_guardrails": {
            "fusion_model_trained":
                False,

            "water_stress_probability_produced":
                False,

            "disease_classification_is_water_stress":
                False,

            "sensor_source_is_simulated_used_as_model_feature":
                False,

            "gradcam_used_as_model_feature":
                False,

            "missing_temporal_features_imputed_as_real_measurement":
                False,

            "temporal_missingness_explicit":
                True,

            "physical_action_authorized":
                False,
        },
    }