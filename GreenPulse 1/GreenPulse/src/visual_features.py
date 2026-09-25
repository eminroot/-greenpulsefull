from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional, Sequence, Union

import numpy as np
from PIL import Image


SCHEMA_VERSION = "greenpulse.visual_features.v1"
FEATURE_VECTOR_VERSION = "visual_feature_vector_v1"

FEATURE_VECTOR_NAMES = [
    "visual_confidence",
    "affected_leaf_area_ratio",
    "affected_leaf_area_available",

    "rgb_r_mean",
    "rgb_g_mean",
    "rgb_b_mean",

    "rgb_r_std",
    "rgb_g_std",
    "rgb_b_std",

    "hsv_h_mean",
    "hsv_s_mean",
    "hsv_v_mean",

    "hsv_h_std",
    "hsv_s_std",
    "hsv_v_std",

    "gray_mean",
    "gray_std",

    "gradient_mean",
    "gradient_std",
    "edge_density",
    "laplacian_energy",

    "relative_visual_change",
    "relative_visual_change_available",
]


ImageLike = Union[
    str,
    Path,
    Image.Image,
    np.ndarray,
]


def _to_rgb_array(
    image: ImageLike,
) -> np.ndarray:

    if isinstance(
        image,
        (str, Path),
    ):
        with Image.open(
            image
        ) as im:
            arr = np.asarray(
                im.convert("RGB"),
                dtype=np.uint8,
            )

    elif isinstance(
        image,
        Image.Image,
    ):
        arr = np.asarray(
            image.convert("RGB"),
            dtype=np.uint8,
        )

    elif isinstance(
        image,
        np.ndarray,
    ):
        arr = np.asarray(
            image
        )

        if arr.ndim == 2:
            arr = np.stack(
                [arr, arr, arr],
                axis=-1,
            )

        if (
            arr.ndim == 3
            and arr.shape[2] == 4
        ):
            arr = arr[
                ...,
                :3
            ]

        if (
            arr.ndim != 3
            or arr.shape[2] != 3
        ):
            raise ValueError(
                "NumPy image must have shape HxWx3 "
                "or HxW."
            )

        if not np.issubdtype(
            arr.dtype,
            np.number,
        ):
            raise ValueError(
                "Image array must be numeric."
            )

        if not np.all(
            np.isfinite(
                arr
            )
        ):
            raise ValueError(
                "Image contains NaN or infinite values."
            )

        minimum = float(
            np.min(
                arr
            )
        )

        maximum = float(
            np.max(
                arr
            )
        )

        if (
            minimum < 0.0
            or maximum > 255.0
        ):
            raise ValueError(
                "Image array values must be in [0, 255]."
            )

        arr = np.rint(
            arr
        ).astype(
            np.uint8
        )

    else:
        raise TypeError(
            "Unsupported image type."
        )

    if (
        arr.shape[0] < 2
        or arr.shape[1] < 2
    ):
        raise ValueError(
            "Image must be at least 2x2 pixels."
        )

    return arr


def _validate_confidence(
    value: float,
) -> float:

    value = float(
        value
    )

    if not np.isfinite(
        value
    ):
        raise ValueError(
            "visual_confidence must be finite."
        )

    if not (
        0.0
        <= value
        <= 1.0
    ):
        raise ValueError(
            "visual_confidence must be in [0, 1]."
        )

    return value


def _normalize_roi(
    roi_xyxy: Optional[
        Sequence[int]
    ],
    width: int,
    height: int,
) -> Optional[
    tuple[int, int, int, int]
]:

    if roi_xyxy is None:
        return None

    if len(
        roi_xyxy
    ) != 4:
        raise ValueError(
            "roi_xyxy must contain exactly "
            "four values: x1, y1, x2, y2."
        )

    x1, y1, x2, y2 = [
        int(v)
        for v in roi_xyxy
    ]

    if not (
        0
        <= x1
        < x2
        <= width
    ):
        raise ValueError(
            "Invalid ROI x coordinates."
        )

    if not (
        0
        <= y1
        < y2
        <= height
    ):
        raise ValueError(
            "Invalid ROI y coordinates."
        )

    return (
        x1,
        y1,
        x2,
        y2,
    )


def _validate_mask(
    mask: Optional[np.ndarray],
    height: int,
    width: int,
    name: str,
) -> Optional[np.ndarray]:

    if mask is None:
        return None

    arr = np.asarray(
        mask
    )

    if arr.shape != (
        height,
        width,
    ):
        raise ValueError(
            f"{name} must match image shape "
            f"{height}x{width}."
        )

    if not np.issubdtype(
        arr.dtype,
        np.number,
    ) and arr.dtype != np.bool_:
        raise ValueError(
            f"{name} must be numeric or boolean."
        )

    if np.issubdtype(
        arr.dtype,
        np.number,
    ):
        if not np.all(
            np.isfinite(
                arr
            )
        ):
            raise ValueError(
                f"{name} contains NaN or infinite values."
            )

    return arr.astype(
        bool
    )


def _rgb_to_hsv(
    rgb_normalized: np.ndarray,
) -> np.ndarray:

    r = rgb_normalized[
        ...,
        0
    ]

    g = rgb_normalized[
        ...,
        1
    ]

    b = rgb_normalized[
        ...,
        2
    ]

    maximum = np.maximum.reduce(
        [r, g, b]
    )

    minimum = np.minimum.reduce(
        [r, g, b]
    )

    delta = (
        maximum
        - minimum
    )

    hue = np.zeros_like(
        maximum
    )

    non_zero = (
        delta > 1e-12
    )

    mask = (
        non_zero
        & (maximum == r)
    )

    hue[
        mask
    ] = (
        (
            (g[mask] - b[mask])
            / delta[mask]
        )
        % 6.0
    )

    mask = (
        non_zero
        & (maximum == g)
    )

    hue[
        mask
    ] = (
        (
            (b[mask] - r[mask])
            / delta[mask]
        )
        + 2.0
    )

    mask = (
        non_zero
        & (maximum == b)
    )

    hue[
        mask
    ] = (
        (
            (r[mask] - g[mask])
            / delta[mask]
        )
        + 4.0
    )

    hue /= 6.0

    saturation = np.zeros_like(
        maximum
    )

    non_black = (
        maximum > 1e-12
    )

    saturation[
        non_black
    ] = (
        delta[
            non_black
        ]
        / maximum[
            non_black
        ]
    )

    value = maximum

    return np.stack(
        [
            hue,
            saturation,
            value,
        ],
        axis=-1,
    )


def _color_statistics(
    rgb: np.ndarray,
) -> dict[str, Any]:

    rgb_float = (
        rgb.astype(
            np.float64
        )
        / 255.0
    )

    flat_rgb = rgb_float.reshape(
        -1,
        3,
    )

    rgb_mean = np.mean(
        flat_rgb,
        axis=0,
    )

    rgb_std = np.std(
        flat_rgb,
        axis=0,
    )

    hsv = _rgb_to_hsv(
        rgb_float
    )

    flat_hsv = hsv.reshape(
        -1,
        3,
    )

    hsv_mean = np.mean(
        flat_hsv,
        axis=0,
    )

    hsv_std = np.std(
        flat_hsv,
        axis=0,
    )

    return {
        "rgb_mean": [
            float(v)
            for v in rgb_mean
        ],

        "rgb_std": [
            float(v)
            for v in rgb_std
        ],

        "hsv_mean": [
            float(v)
            for v in hsv_mean
        ],

        "hsv_std": [
            float(v)
            for v in hsv_std
        ],
    }


def _texture_statistics(
    rgb: np.ndarray,
    edge_threshold: float,
) -> dict[str, float]:

    rgb_float = (
        rgb.astype(
            np.float64
        )
        / 255.0
    )

    gray = (
        0.299
        * rgb_float[
            ...,
            0
        ]
        +
        0.587
        * rgb_float[
            ...,
            1
        ]
        +
        0.114
        * rgb_float[
            ...,
            2
        ]
    )

    dx = np.diff(
        gray,
        axis=1,
    )

    dy = np.diff(
        gray,
        axis=0,
    )

    gradient_values = np.concatenate(
        [
            np.abs(
                dx
            ).ravel(),
            np.abs(
                dy
            ).ravel(),
        ]
    )

    gradient_mean = float(
        np.mean(
            gradient_values
        )
    )

    gradient_std = float(
        np.std(
            gradient_values
        )
    )

    edge_density = float(
        np.mean(
            gradient_values
            >= edge_threshold
        )
    )

    if (
        gray.shape[0] >= 3
        and gray.shape[1] >= 3
    ):
        center = gray[
            1:-1,
            1:-1
        ]

        laplacian = (
            -4.0
            * center
            +
            gray[
                :-2,
                1:-1
            ]
            +
            gray[
                2:,
                1:-1
            ]
            +
            gray[
                1:-1,
                :-2
            ]
            +
            gray[
                1:-1,
                2:
            ]
        )

        laplacian_energy = float(
            np.mean(
                np.square(
                    laplacian
                )
            )
        )

    else:
        laplacian_energy = 0.0

    return {
        "gray_mean":
            float(
                np.mean(
                    gray
                )
            ),

        "gray_std":
            float(
                np.std(
                    gray
                )
            ),

        "gradient_mean":
            gradient_mean,

        "gradient_std":
            gradient_std,

        "edge_density":
            edge_density,

        "laplacian_energy":
            laplacian_energy,
    }


def _affected_area(
    leaf_mask: Optional[np.ndarray],
    affected_mask: Optional[np.ndarray],
) -> dict[str, Any]:

    result = {
        "affected_leaf_area_ratio":
            None,

        "affected_image_area_ratio":
            None,

        "leaf_area_available":
            leaf_mask is not None,

        "affected_area_available":
            affected_mask is not None,

        "affected_leaf_area_available":
            (
                leaf_mask is not None
                and affected_mask is not None
            ),

        "source":
            "UNAVAILABLE",
    }

    if affected_mask is None:
        return result

    result[
        "affected_image_area_ratio"
    ] = float(
        np.mean(
            affected_mask
        )
    )

    if leaf_mask is None:
        result[
            "source"
        ] = "AFFECTED_MASK_ONLY"
        return result

    leaf_pixels = int(
        np.count_nonzero(
            leaf_mask
        )
    )

    if leaf_pixels == 0:
        raise ValueError(
            "leaf_mask contains no positive pixels."
        )

    affected_inside_leaf = (
        affected_mask
        & leaf_mask
    )

    affected_leaf_pixels = int(
        np.count_nonzero(
            affected_inside_leaf
        )
    )

    affected_outside_leaf_pixels = int(
        np.count_nonzero(
            affected_mask
            & ~leaf_mask
        )
    )

    result.update({
        "affected_leaf_area_ratio":
            float(
                affected_leaf_pixels
                / leaf_pixels
            ),

        "leaf_pixels":
            leaf_pixels,

        "affected_leaf_pixels":
            affected_leaf_pixels,

        "affected_outside_leaf_pixels":
            affected_outside_leaf_pixels,

        "source":
            "VALIDATED_LEAF_AND_AFFECTED_MASKS",
    })

    return result


def build_visual_baseline_signature(
    visual_features: Mapping[str, Any],
) -> dict[str, Any]:

    return {
        "schema_version":
            "greenpulse.visual_baseline_signature.v1",

        "rgb_mean":
            list(
                visual_features[
                    "color_statistics"
                ][
                    "rgb_mean"
                ]
            ),

        "hsv_mean":
            list(
                visual_features[
                    "color_statistics"
                ][
                    "hsv_mean"
                ]
            ),

        "gray_mean":
            float(
                visual_features[
                    "texture_statistics"
                ][
                    "gray_mean"
                ]
            ),

        "gradient_mean":
            float(
                visual_features[
                    "texture_statistics"
                ][
                    "gradient_mean"
                ]
            ),

        "edge_density":
            float(
                visual_features[
                    "texture_statistics"
                ][
                    "edge_density"
                ]
            ),

        "laplacian_energy":
            float(
                visual_features[
                    "texture_statistics"
                ][
                    "laplacian_energy"
                ]
            ),
    }


def _relative_visual_change(
    color_statistics: Mapping[str, Any],
    texture_statistics: Mapping[str, Any],
    baseline_signature: Optional[
        Mapping[str, Any]
    ],
) -> dict[str, Any]:

    if baseline_signature is None:
        return {
            "available":
                False,

            "score":
                None,

            "component_deltas":
                None,
        }

    required = [
        "rgb_mean",
        "hsv_mean",
        "gray_mean",
        "gradient_mean",
        "edge_density",
        "laplacian_energy",
    ]

    missing = [
        key
        for key in required
        if key not in baseline_signature
    ]

    if missing:
        raise ValueError(
            "Baseline signature missing fields: "
            + ", ".join(
                missing
            )
        )

    current_rgb = np.asarray(
        color_statistics[
            "rgb_mean"
        ],
        dtype=np.float64,
    )

    baseline_rgb = np.asarray(
        baseline_signature[
            "rgb_mean"
        ],
        dtype=np.float64,
    )

    current_hsv = np.asarray(
        color_statistics[
            "hsv_mean"
        ],
        dtype=np.float64,
    )

    baseline_hsv = np.asarray(
        baseline_signature[
            "hsv_mean"
        ],
        dtype=np.float64,
    )

    if (
        current_rgb.shape != (3,)
        or baseline_rgb.shape != (3,)
        or current_hsv.shape != (3,)
        or baseline_hsv.shape != (3,)
    ):
        raise ValueError(
            "Baseline RGB/HSV means must contain "
            "three values."
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

    gray_delta = abs(
        float(
            texture_statistics[
                "gray_mean"
            ]
        )
        -
        float(
            baseline_signature[
                "gray_mean"
            ]
        )
    )

    gradient_delta = abs(
        float(
            texture_statistics[
                "gradient_mean"
            ]
        )
        -
        float(
            baseline_signature[
                "gradient_mean"
            ]
        )
    )

    edge_delta = abs(
        float(
            texture_statistics[
                "edge_density"
            ]
        )
        -
        float(
            baseline_signature[
                "edge_density"
            ]
        )
    )

    current_laplacian = float(
        texture_statistics[
            "laplacian_energy"
        ]
    )

    baseline_laplacian = float(
        baseline_signature[
            "laplacian_energy"
        ]
    )

    laplacian_delta = (
        abs(
            current_laplacian
            - baseline_laplacian
        )
        /
        (
            1.0
            + abs(
                baseline_laplacian
            )
        )
    )

    component_deltas = {
        "rgb_mean_delta":
            rgb_delta,

        "hsv_mean_delta":
            hsv_delta,

        "gray_mean_delta":
            gray_delta,

        "gradient_mean_delta":
            gradient_delta,

        "edge_density_delta":
            edge_delta,

        "laplacian_energy_delta":
            laplacian_delta,
    }

    score = float(
        np.mean(
            list(
                component_deltas.values()
            )
        )
    )

    return {
        "available":
            True,

        "score":
            score,

        "component_deltas":
            component_deltas,
    }


def extract_visual_features(
    image: ImageLike,
    *,
    visual_confidence: float,
    confidence_source: str,
    roi_xyxy: Optional[
        Sequence[int]
    ] = None,
    leaf_mask: Optional[
        np.ndarray
    ] = None,
    affected_mask: Optional[
        np.ndarray
    ] = None,
    baseline_signature: Optional[
        Mapping[str, Any]
    ] = None,
    edge_threshold: float = 0.08,
) -> dict[str, Any]:

    confidence = _validate_confidence(
        visual_confidence
    )

    if not isinstance(
        confidence_source,
        str,
    ) or not confidence_source.strip():
        raise ValueError(
            "confidence_source must be a "
            "non-empty string."
        )

    edge_threshold = float(
        edge_threshold
    )

    if not (
        0.0
        <= edge_threshold
        <= 1.0
    ):
        raise ValueError(
            "edge_threshold must be in [0, 1]."
        )

    rgb = _to_rgb_array(
        image
    )

    height, width = rgb.shape[
        :2
    ]

    normalized_roi = _normalize_roi(
        roi_xyxy,
        width,
        height,
    )

    validated_leaf_mask = _validate_mask(
        leaf_mask,
        height,
        width,
        "leaf_mask",
    )

    validated_affected_mask = _validate_mask(
        affected_mask,
        height,
        width,
        "affected_mask",
    )

    if normalized_roi is None:
        analysis_rgb = rgb
    else:
        x1, y1, x2, y2 = normalized_roi

        analysis_rgb = rgb[
            y1:y2,
            x1:x2,
        ]

    color_statistics = _color_statistics(
        analysis_rgb
    )

    texture_statistics = _texture_statistics(
        analysis_rgb,
        edge_threshold=edge_threshold,
    )

    affected_area = _affected_area(
        validated_leaf_mask,
        validated_affected_mask,
    )

    relative_change = _relative_visual_change(
        color_statistics,
        texture_statistics,
        baseline_signature,
    )

    affected_leaf_ratio = (
        affected_area[
            "affected_leaf_area_ratio"
        ]
        if affected_area[
            "affected_leaf_area_ratio"
        ] is not None
        else 0.0
    )

    relative_change_score = (
        relative_change[
            "score"
        ]
        if relative_change[
            "score"
        ] is not None
        else 0.0
    )

    vector_values = [
        confidence,

        float(
            affected_leaf_ratio
        ),

        float(
            affected_area[
                "affected_leaf_area_available"
            ]
        ),

        *[
            float(v)
            for v in color_statistics[
                "rgb_mean"
            ]
        ],

        *[
            float(v)
            for v in color_statistics[
                "rgb_std"
            ]
        ],

        *[
            float(v)
            for v in color_statistics[
                "hsv_mean"
            ]
        ],

        *[
            float(v)
            for v in color_statistics[
                "hsv_std"
            ]
        ],

        float(
            texture_statistics[
                "gray_mean"
            ]
        ),

        float(
            texture_statistics[
                "gray_std"
            ]
        ),

        float(
            texture_statistics[
                "gradient_mean"
            ]
        ),

        float(
            texture_statistics[
                "gradient_std"
            ]
        ),

        float(
            texture_statistics[
                "edge_density"
            ]
        ),

        float(
            texture_statistics[
                "laplacian_energy"
            ]
        ),

        float(
            relative_change_score
        ),

        float(
            relative_change[
                "available"
            ]
        ),
    ]

    if len(
        vector_values
    ) != len(
        FEATURE_VECTOR_NAMES
    ):
        raise RuntimeError(
            "Feature-vector schema mismatch."
        )

    if not np.all(
        np.isfinite(
            np.asarray(
                vector_values,
                dtype=np.float64,
            )
        )
    ):
        raise RuntimeError(
            "Feature vector contains non-finite values."
        )

    return {
        "schema_version":
            SCHEMA_VERSION,

        "feature_vector_version":
            FEATURE_VECTOR_VERSION,

        "source": {
            "image_height":
                int(
                    height
                ),

            "image_width":
                int(
                    width
                ),

            "analysis_region":
                (
                    "FULL_IMAGE"
                    if normalized_roi is None
                    else "ROI"
                ),

            "roi_xyxy":
                (
                    list(
                        normalized_roi
                    )
                    if normalized_roi is not None
                    else None
                ),

            "pixel_array_contract":
                "RGB_0_255",
        },

        "visual_confidence": {
            "value":
                confidence,

            "source":
                confidence_source.strip(),
        },

        "affected_area":
            affected_area,

        "color_statistics":
            color_statistics,

        "texture_statistics":
            texture_statistics,

        "relative_visual_change":
            relative_change,

        "feature_vector": {
            "names":
                list(
                    FEATURE_VECTOR_NAMES
                ),

            "values":
                vector_values,

            "length":
                len(
                    vector_values
                ),

            "missing_value_policy":
                (
                    "Unavailable numeric features are encoded as "
                    "0.0 only together with an explicit availability "
                    "flag in the vector."
                ),
        },

        "scientific_guardrails": {
            "affected_leaf_area_claim_allowed":
                bool(
                    affected_area[
                        "affected_leaf_area_available"
                    ]
                ),

            "affected_leaf_area_requires":
                (
                    "validated leaf_mask + "
                    "validated affected_mask"
                ),

            "bbox_alone_is_not_affected_area":
                True,

            "classification_confidence_is_not_detection_confidence":
                (
                    confidence_source.strip().lower()
                    == "classification"
                ),

            "relative_change_is_not_early_stress_proof":
                True,

            "physical_action_authorized":
                False,
        },
    }
