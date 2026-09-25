from __future__ import annotations

from typing import Any, Mapping, Optional, Sequence

import numpy as np


BASELINE_SCHEMA_VERSION = "greenpulse.plant_baseline.v1"
DELTA_SCHEMA_VERSION = "greenpulse.plant_delta.v1"


TEXTURE_KEYS = [
    "gray_mean",
    "gray_std",
    "gradient_mean",
    "gradient_std",
    "edge_density",
    "laplacian_energy",
]


def _finite_float(
    value: Any,
    name: str,
) -> float:

    result = float(value)

    if not np.isfinite(result):
        raise ValueError(
            f"{name} must be finite."
        )

    return result


def _validate_visual_features(
    visual_features: Mapping[str, Any],
) -> None:

    required = [
        "schema_version",
        "visual_confidence",
        "affected_area",
        "color_statistics",
        "texture_statistics",
    ]

    missing = [
        key
        for key in required
        if key not in visual_features
    ]

    if missing:
        raise ValueError(
            "Visual feature record missing fields: "
            + ", ".join(missing)
        )

    if (
        visual_features["schema_version"]
        != "greenpulse.visual_features.v1"
    ):
        raise ValueError(
            "Unsupported visual feature schema."
        )

    color = visual_features[
        "color_statistics"
    ]

    for key in (
        "rgb_mean",
        "hsv_mean",
    ):
        values = np.asarray(
            color[key],
            dtype=np.float64,
        )

        if values.shape != (3,):
            raise ValueError(
                f"{key} must contain 3 values."
            )

        if not np.all(
            np.isfinite(values)
        ):
            raise ValueError(
                f"{key} contains non-finite values."
            )

    texture = visual_features[
        "texture_statistics"
    ]

    for key in TEXTURE_KEYS:
        _finite_float(
            texture[key],
            f"texture_statistics.{key}",
        )

    confidence = _finite_float(
        visual_features[
            "visual_confidence"
        ][
            "value"
        ],
        "visual_confidence.value",
    )

    if not (
        0.0
        <= confidence
        <= 1.0
    ):
        raise ValueError(
            "Visual confidence must be in [0, 1]."
        )


def _validate_identity(
    plant_id: Optional[str],
    cohort_id: Optional[str],
) -> tuple[str, str]:

    has_plant = bool(
        isinstance(
            plant_id,
            str,
        )
        and plant_id.strip()
    )

    has_cohort = bool(
        isinstance(
            cohort_id,
            str,
        )
        and cohort_id.strip()
    )

    if has_plant == has_cohort:
        raise ValueError(
            "Exactly one of plant_id or cohort_id "
            "must be provided."
        )

    if has_plant:
        return (
            "PLANT",
            plant_id.strip(),
        )

    return (
        "COHORT",
        cohort_id.strip(),
    )


def _aggregate(
    values: Sequence[float],
    method: str,
) -> float:

    arr = np.asarray(
        values,
        dtype=np.float64,
    )

    if arr.size == 0:
        raise ValueError(
            "Cannot aggregate an empty sequence."
        )

    if not np.all(
        np.isfinite(arr)
    ):
        raise ValueError(
            "Aggregation input contains "
            "non-finite values."
        )

    ordered = np.sort(
        arr,
        axis=None,
    )

    if method == "mean":
        return float(
            np.mean(
                ordered
            )
        )

    if method == "median":
        return float(
            np.median(
                ordered
            )
        )

    raise ValueError(
        "aggregation_method must be "
        "'mean' or 'median'."
    )


def _aggregate_vector(
    vectors: Sequence[Sequence[float]],
    method: str,
) -> list[float]:

    arr = np.asarray(
        vectors,
        dtype=np.float64,
    )

    if (
        arr.ndim != 2
        or arr.shape[1] != 3
    ):
        raise ValueError(
            "Expected Nx3 vectors."
        )

    if not np.all(
        np.isfinite(arr)
    ):
        raise ValueError(
            "Vector aggregation contains "
            "non-finite values."
        )

    ordered = np.sort(
        arr,
        axis=0,
    )

    if method == "mean":
        result = np.mean(
            ordered,
            axis=0,
        )

    elif method == "median":
        result = np.median(
            ordered,
            axis=0,
        )

    else:
        raise ValueError(
            "aggregation_method must be "
            "'mean' or 'median'."
        )

    return [
        float(v)
        for v in result
    ]


def build_plant_baseline(
    observations: Sequence[
        Mapping[str, Any]
    ],
    *,
    plant_id: Optional[str] = None,
    cohort_id: Optional[str] = None,
    min_healthy_observations: int = 3,
    aggregation_method: str = "mean",
) -> dict[str, Any]:

    identity_type, identity_value = (
        _validate_identity(
            plant_id,
            cohort_id,
        )
    )

    min_healthy_observations = int(
        min_healthy_observations
    )

    if min_healthy_observations < 2:
        raise ValueError(
            "min_healthy_observations must be >= 2."
        )

    if aggregation_method not in {
        "mean",
        "median",
    }:
        raise ValueError(
            "aggregation_method must be "
            "'mean' or 'median'."
        )

    healthy_records = []

    for observation in observations:

        if not isinstance(
            observation,
            Mapping,
        ):
            raise TypeError(
                "Each observation must be a mapping."
            )

        if observation.get(
            "is_healthy"
        ) is not True:
            continue

        if identity_type == "PLANT":

            if (
                observation.get(
                    "plant_id"
                )
                != identity_value
            ):
                continue

        else:

            if (
                observation.get(
                    "cohort_id"
                )
                != identity_value
            ):
                continue

        if "visual_features" not in observation:
            raise ValueError(
                "Healthy observation missing "
                "visual_features."
            )

        _validate_visual_features(
            observation[
                "visual_features"
            ]
        )

        healthy_records.append(
            observation
        )

    if len(
        healthy_records
    ) < min_healthy_observations:

        raise ValueError(
            "Insufficient healthy observations "
            f"for baseline: {len(healthy_records)} "
            f"< {min_healthy_observations}."
        )

    rgb_means = []

    hsv_means = []

    confidence_values = []

    texture_values = {
        key: []
        for key in TEXTURE_KEYS
    }

    affected_ratios = []

    observation_ids = []

    timestamps = []

    for observation in healthy_records:

        visual = observation[
            "visual_features"
        ]

        color = visual[
            "color_statistics"
        ]

        texture = visual[
            "texture_statistics"
        ]

        rgb_means.append(
            color[
                "rgb_mean"
            ]
        )

        hsv_means.append(
            color[
                "hsv_mean"
            ]
        )

        confidence_values.append(
            _finite_float(
                visual[
                    "visual_confidence"
                ][
                    "value"
                ],
                "visual_confidence.value",
            )
        )

        for key in TEXTURE_KEYS:

            texture_values[
                key
            ].append(
                _finite_float(
                    texture[key],
                    key,
                )
            )

        area = visual[
            "affected_area"
        ]

        if (
            area.get(
                "affected_leaf_area_available"
            ) is True
            and area.get(
                "affected_leaf_area_ratio"
            ) is not None
        ):

            ratio = _finite_float(
                area[
                    "affected_leaf_area_ratio"
                ],
                "affected_leaf_area_ratio",
            )

            if not (
                0.0
                <= ratio
                <= 1.0
            ):
                raise ValueError(
                    "affected_leaf_area_ratio "
                    "must be in [0, 1]."
                )

            affected_ratios.append(
                ratio
            )

        observation_id = observation.get(
            "observation_id"
        )

        if observation_id is not None:
            observation_ids.append(
                str(
                    observation_id
                )
            )

        timestamp = observation.get(
            "timestamp"
        )

        if timestamp is not None:
            timestamps.append(
                str(
                    timestamp
                )
            )

    baseline_texture = {
        key:
            _aggregate(
                values,
                aggregation_method,
            )
        for key, values
        in texture_values.items()
    }

    affected_available = (
        len(
            affected_ratios
        ) > 0
    )

    affected_mean = (
        _aggregate(
            affected_ratios,
            aggregation_method,
        )
        if affected_available
        else None
    )

    return {
        "schema_version":
            BASELINE_SCHEMA_VERSION,

        "identity": {
            "type":
                identity_type,

            "id":
                identity_value,
        },

        "baseline_status":
            "READY",

        "healthy_observation_count":
            len(
                healthy_records
            ),

        "minimum_required":
            min_healthy_observations,

        "aggregation_method":
            aggregation_method,

        "color_baseline": {
            "rgb_mean":
                _aggregate_vector(
                    rgb_means,
                    aggregation_method,
                ),

            "hsv_mean":
                _aggregate_vector(
                    hsv_means,
                    aggregation_method,
                ),
        },

        "texture_baseline":
            baseline_texture,

        "confidence_baseline": {
            "mean":
                _aggregate(
                    confidence_values,
                    aggregation_method,
                ),
        },

        "affected_area_baseline": {
            "available":
                affected_available,

            "affected_leaf_area_ratio":
                affected_mean,

            "validated_area_observation_count":
                len(
                    affected_ratios
                ),
        },

        "provenance": {
            "observation_ids":
                sorted(
                    observation_ids
                ),

            "timestamps":
                sorted(
                    timestamps
                ),

            "healthy_only":
                True,
        },

        "update_policy": {
            "automatic_update_allowed":
                False,

            "manual_or_controlled_rebuild_required":
                True,
        },

        "scientific_guardrails": {
            "baseline_is_real_plant_evidence":
                False,

            "early_stress_claim_allowed":
                False,

            "affected_area_used_only_when_validated":
                True,

            "physical_action_authorized":
                False,
        },
    }


def compute_plant_delta(
    current_visual_features: Mapping[
        str,
        Any,
    ],
    baseline: Mapping[
        str,
        Any,
    ],
) -> dict[str, Any]:

    _validate_visual_features(
        current_visual_features
    )

    if (
        baseline.get(
            "schema_version"
        )
        != BASELINE_SCHEMA_VERSION
    ):
        raise ValueError(
            "Unsupported baseline schema."
        )

    if (
        baseline.get(
            "baseline_status"
        )
        != "READY"
    ):
        raise ValueError(
            "Baseline is not READY."
        )

    current_color = current_visual_features[
        "color_statistics"
    ]

    current_texture = current_visual_features[
        "texture_statistics"
    ]

    baseline_color = baseline[
        "color_baseline"
    ]

    baseline_texture = baseline[
        "texture_baseline"
    ]

    current_rgb = np.asarray(
        current_color[
            "rgb_mean"
        ],
        dtype=np.float64,
    )

    baseline_rgb = np.asarray(
        baseline_color[
            "rgb_mean"
        ],
        dtype=np.float64,
    )

    current_hsv = np.asarray(
        current_color[
            "hsv_mean"
        ],
        dtype=np.float64,
    )

    baseline_hsv = np.asarray(
        baseline_color[
            "hsv_mean"
        ],
        dtype=np.float64,
    )

    rgb_delta = float(
        np.mean(
            np.abs(
                current_rgb
                - baseline_rgb
            )
        )
    )

    hsv_delta = float(
        np.mean(
            np.abs(
                current_hsv
                - baseline_hsv
            )
        )
    )

    color_delta = float(
        np.mean(
            [
                rgb_delta,
                hsv_delta,
            ]
        )
    )

    texture_components = {}

    for key in TEXTURE_KEYS:

        current_value = _finite_float(
            current_texture[
                key
            ],
            key,
        )

        baseline_value = _finite_float(
            baseline_texture[
                key
            ],
            f"baseline.{key}",
        )

        texture_components[
            key + "_delta"
        ] = abs(
            current_value
            - baseline_value
        )

    texture_delta = float(
        np.mean(
            list(
                texture_components.values()
            )
        )
    )

    current_confidence = _finite_float(
        current_visual_features[
            "visual_confidence"
        ][
            "value"
        ],
        "visual_confidence.value",
    )

    baseline_confidence = _finite_float(
        baseline[
            "confidence_baseline"
        ][
            "mean"
        ],
        "baseline confidence",
    )

    confidence_delta_signed = (
        current_confidence
        - baseline_confidence
    )

    confidence_delta = abs(
        confidence_delta_signed
    )

    current_area = current_visual_features[
        "affected_area"
    ]

    baseline_area = baseline[
        "affected_area_baseline"
    ]

    affected_area_delta = None

    affected_area_delta_signed = None

    affected_area_delta_available = False

    if (
        current_area.get(
            "affected_leaf_area_available"
        ) is True
        and current_area.get(
            "affected_leaf_area_ratio"
        ) is not None
        and baseline_area.get(
            "available"
        ) is True
        and baseline_area.get(
            "affected_leaf_area_ratio"
        ) is not None
    ):

        current_ratio = _finite_float(
            current_area[
                "affected_leaf_area_ratio"
            ],
            "current affected area",
        )

        baseline_ratio = _finite_float(
            baseline_area[
                "affected_leaf_area_ratio"
            ],
            "baseline affected area",
        )

        affected_area_delta_signed = (
            current_ratio
            - baseline_ratio
        )

        affected_area_delta = abs(
            affected_area_delta_signed
        )

        affected_area_delta_available = True

    return {
        "schema_version":
            DELTA_SCHEMA_VERSION,

        "baseline_schema_version":
            BASELINE_SCHEMA_VERSION,

        "identity":
            dict(
                baseline[
                    "identity"
                ]
            ),

        "color_delta": {
            "score":
                color_delta,

            "rgb_mean_absolute_delta":
                rgb_delta,

            "hsv_mean_absolute_delta":
                hsv_delta,
        },

        "texture_delta": {
            "score":
                texture_delta,

            "components":
                texture_components,
        },

        "confidence_delta": {
            "absolute":
                float(
                    confidence_delta
                ),

            "signed":
                float(
                    confidence_delta_signed
                ),

            "current":
                current_confidence,

            "baseline":
                baseline_confidence,
        },

        "affected_area_delta": {
            "available":
                affected_area_delta_available,

            "absolute":
                (
                    float(
                        affected_area_delta
                    )
                    if affected_area_delta
                    is not None
                    else None
                ),

            "signed":
                (
                    float(
                        affected_area_delta_signed
                    )
                    if affected_area_delta_signed
                    is not None
                    else None
                ),
        },

        "scientific_guardrails": {
            "delta_is_not_early_stress_proof":
                True,

            "delta_is_not_causal_evidence":
                True,

            "affected_area_delta_requires_validated_masks":
                True,

            "physical_action_authorized":
                False,
        },
    }