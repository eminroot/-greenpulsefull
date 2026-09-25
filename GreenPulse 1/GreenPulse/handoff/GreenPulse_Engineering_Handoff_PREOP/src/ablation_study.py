from __future__ import annotations

from typing import Any, Sequence


SCHEMA_VERSION = (
    "greenpulse.ablation_study.v1"
)

REAL_SCOPE = (
    "REAL_VALIDATED_MULTIMODAL_DATASET"
)

SYNTHETIC_SCOPE = (
    "SYNTHETIC_TEST_FIXTURE"
)


def _validate_binary_vector(
    values: Sequence[int],
    name: str,
) -> list[int]:

    result = list(values)

    if not result:
        raise ValueError(
            f"{name} must not be empty."
        )

    if any(
        value not in (0, 1)
        for value in result
    ):
        raise ValueError(
            f"{name} must contain only 0/1."
        )

    return result


def binary_classification_metrics(
    y_true: Sequence[int],
    y_pred: Sequence[int],
) -> dict[str, Any]:

    truth = _validate_binary_vector(
        y_true,
        "y_true",
    )

    pred = _validate_binary_vector(
        y_pred,
        "y_pred",
    )

    if len(truth) != len(pred):
        raise ValueError(
            "y_true and y_pred length mismatch."
        )

    tp = sum(
        1
        for t, p in zip(truth, pred)
        if t == 1 and p == 1
    )

    tn = sum(
        1
        for t, p in zip(truth, pred)
        if t == 0 and p == 0
    )

    fp = sum(
        1
        for t, p in zip(truth, pred)
        if t == 0 and p == 1
    )

    fn = sum(
        1
        for t, p in zip(truth, pred)
        if t == 1 and p == 0
    )

    precision = (
        tp / (tp + fp)
        if (tp + fp)
        else 0.0
    )

    recall = (
        tp / (tp + fn)
        if (tp + fn)
        else 0.0
    )

    f1 = (
        2 * precision * recall
        / (precision + recall)
        if (precision + recall)
        else 0.0
    )

    fpr = (
        fp / (fp + tn)
        if (fp + tn)
        else 0.0
    )

    fnr = (
        fn / (fn + tp)
        if (fn + tp)
        else 0.0
    )

    return {
        "support":
            len(truth),

        "tp":
            tp,

        "tn":
            tn,

        "fp":
            fp,

        "fn":
            fn,

        "precision":
            precision,

        "recall":
            recall,

        "f1":
            f1,

        "false_positive_rate":
            fpr,

        "false_negative_rate":
            fnr,
    }


def evaluate_three_way_ablation(
    *,
    y_true: Sequence[int],
    sensor_only: Sequence[int],
    vision_only: Sequence[int],
    fusion: Sequence[int],
    evidence_scope: str,
) -> dict[str, Any]:

    if evidence_scope not in {
        SYNTHETIC_SCOPE,
        REAL_SCOPE,
    }:
        raise ValueError(
            "Unsupported evidence_scope."
        )

    truth = _validate_binary_vector(
        y_true,
        "y_true",
    )

    sensor = _validate_binary_vector(
        sensor_only,
        "sensor_only",
    )

    vision = _validate_binary_vector(
        vision_only,
        "vision_only",
    )

    fused = _validate_binary_vector(
        fusion,
        "fusion",
    )

    lengths = {
        len(truth),
        len(sensor),
        len(vision),
        len(fused),
    }

    if len(lengths) != 1:
        raise ValueError(
            "All ablation vectors must have equal length."
        )

    metrics = {
        "sensor_only":
            binary_classification_metrics(
                truth,
                sensor,
            ),

        "vision_only":
            binary_classification_metrics(
                truth,
                vision,
            ),

        "vision_sensor_fusion":
            binary_classification_metrics(
                truth,
                fused,
            ),
    }

    sensor_f1 = metrics[
        "sensor_only"
    ][
        "f1"
    ]

    vision_f1 = metrics[
        "vision_only"
    ][
        "f1"
    ]

    fusion_f1 = metrics[
        "vision_sensor_fusion"
    ][
        "f1"
    ]

    fusion_f1_above_both = (
        fusion_f1 > sensor_f1
        and fusion_f1 > vision_f1
    )

    claim_permitted = (
        evidence_scope == REAL_SCOPE
        and fusion_f1_above_both
    )

    return {
        "schema_version":
            SCHEMA_VERSION,

        "evidence_scope":
            evidence_scope,

        "sample_count":
            len(truth),

        "metrics":
            metrics,

        "comparisons": {
            "fusion_f1_above_sensor_only":
                fusion_f1 > sensor_f1,

            "fusion_f1_above_vision_only":
                fusion_f1 > vision_f1,

            "fusion_f1_above_both":
                fusion_f1_above_both,
        },

        "claim_boundary": {
            "real_dataset_used":
                evidence_scope == REAL_SCOPE,

            "multimodal_benefit_claim_permitted":
                claim_permitted,

            "synthetic_result_may_be_claimed_real":
                False,
        },
    }