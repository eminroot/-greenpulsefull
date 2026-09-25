
import hashlib
import json
import math

from pathlib import Path


def sha256_file(path):
    digest = hashlib.sha256()

    with Path(path).open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b""
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path):
    path = Path(path)

    if not path.is_file():
        raise FileNotFoundError(path)

    return json.loads(
        path.read_text(
            encoding="utf-8-sig"
        )
    )


def validate_protocol(protocol):

    if protocol.get("version") != "1.0":
        raise ValueError(
            "INVALID_PROTOCOL_VERSION"
        )

    if protocol.get("mode") != "RESEARCH_ONLY":
        raise ValueError(
            "UNSAFE_PROTOCOL_MODE"
        )

    arms = protocol.get(
        "required_experiment_arms"
    )

    if arms != [
        "SOURCE_CROP_PRETRAINED",
        "GENERIC_PRETRAINED_BASELINE"
    ]:
        raise ValueError(
            "INVALID_EXPERIMENT_ARMS"
        )

    controls = protocol.get(
        "required_controls",
        {}
    )

    if not controls:
        raise ValueError(
            "MISSING_EXPERIMENT_CONTROLS"
        )

    if not all(
        value is True
        for value in controls.values()
    ):
        raise ValueError(
            "EXPERIMENT_CONTROLS_NOT_STRICT"
        )

    future = protocol.get(
        "future_adaptation_training",
        {}
    )

    required_future = {
        "freeze_strategy_must_be_declared_before_training",
        "selected_backbone_freeze_required_for_protocol_arm",
        "freeze_configuration_must_be_recorded"
    }

    if set(future) != required_future:
        raise ValueError(
            "INVALID_FREEZE_POLICY"
        )

    if not all(
        future[key] is True
        for key in required_future
    ):
        raise ValueError(
            "UNSAFE_FREEZE_POLICY"
        )

    test_policy = protocol.get(
        "held_out_test_policy",
        {}
    )

    if (
        test_policy.get(
            "use_for_model_selection"
        ) is not False
        or test_policy.get(
            "use_for_threshold_tuning"
        ) is not False
        or test_policy.get(
            "single_final_evaluation_only"
        ) is not True
    ):
        raise ValueError(
            "UNSAFE_TEST_POLICY"
        )

    if protocol.get(
        "physical_actuation_allowed"
    ) is not False:
        raise ValueError(
            "ACTUATION_MUST_BE_DISABLED"
        )

    return True


def _finite_metric(value, name):

    if (
        isinstance(value, bool)
        or not isinstance(
            value,
            (int, float)
        )
        or not math.isfinite(value)
        or not 0 <= value <= 1
    ):
        raise ValueError(
            f"INVALID_METRIC_{name}"
        )

    return float(value)


def evaluate_adaptation_evidence(
    transfer_training,
    baseline_training,
    comparison,
    final_test,
    protocol
):

    validate_protocol(
        protocol
    )

    if transfer_training.get(
        "training_completed"
    ) is not True:
        raise ValueError(
            "TRANSFER_TRAINING_INCOMPLETE"
        )

    if baseline_training.get(
        "training_completed"
    ) is not True:
        raise ValueError(
            "BASELINE_TRAINING_INCOMPLETE"
        )

    if comparison.get(
        "comparison_split"
    ) != "VALIDATION_ONLY":
        raise ValueError(
            "COMPARISON_NOT_VALIDATION_ONLY"
        )

    if comparison.get(
        "test_images_evaluated"
    ) != 0:
        raise ValueError(
            "TEST_CONTAMINATED_MODEL_COMPARISON"
        )

    if final_test.get(
        "evaluation_split"
    ) != "FROZEN_FINAL_TEST":
        raise ValueError(
            "INVALID_FINAL_TEST"
        )

    if final_test.get(
        "test_used_for_model_selection"
    ) is not False:
        raise ValueError(
            "TEST_USED_FOR_MODEL_SELECTION"
        )

    transfer_hash = (
        transfer_training.get(
            "best_checkpoint_sha256"
        )
    )

    baseline_hash = (
        baseline_training.get(
            "best_checkpoint_sha256"
        )
    )

    if (
        comparison.get(
            "transfer_checkpoint_sha256"
        ) != transfer_hash
    ):
        raise ValueError(
            "TRANSFER_CHECKPOINT_MISMATCH"
        )

    if (
        comparison.get(
            "baseline_checkpoint_sha256"
        ) != baseline_hash
    ):
        raise ValueError(
            "BASELINE_CHECKPOINT_MISMATCH"
        )

    if (
        final_test.get(
            "checkpoint_sha256"
        ) != transfer_hash
    ):
        raise ValueError(
            "FINAL_TEST_CHECKPOINT_MISMATCH"
        )

    transfer_metrics = comparison.get(
        "transfer_metrics",
        {}
    )

    baseline_metrics = comparison.get(
        "baseline_metrics",
        {}
    )

    required_metrics = [
        "accuracy",
        "balanced_accuracy",
        "macro_precision",
        "macro_recall",
        "macro_f1"
    ]

    for metric in required_metrics:

        _finite_metric(
            transfer_metrics.get(metric),
            "TRANSFER_" + metric
        )

        _finite_metric(
            baseline_metrics.get(metric),
            "BASELINE_" + metric
        )

    transfer_f1 = float(
        transfer_metrics[
            "macro_f1"
        ]
    )

    baseline_f1 = float(
        baseline_metrics[
            "macro_f1"
        ]
    )

    observed_difference = (
        transfer_f1
        - baseline_f1
    )

    reported_difference = float(
        comparison.get(
            "observed_macro_f1_difference"
        )
    )

    if not math.isclose(
        observed_difference,
        reported_difference,
        abs_tol=1e-12
    ):
        raise ValueError(
            "COMPARISON_DIFFERENCE_MISMATCH"
        )

    paired = comparison.get(
        "paired_results",
        {}
    )

    total_paired = sum(
        int(
            paired.get(key, 0)
        )
        for key in (
            "both_correct",
            "transfer_only_correct",
            "baseline_only_correct",
            "both_wrong"
        )
    )

    if (
        total_paired
        != comparison.get(
            "validation_images"
        )
    ):
        raise ValueError(
            "PAIRED_VALIDATION_COUNT_MISMATCH"
        )

    # Current pepper training report does not
    # contain a predeclared backbone freeze
    # strategy. Therefore we must NOT claim that
    # the documented frozen-backbone adaptation
    # protocol was performed.
    freeze_strategy = (
        transfer_training.get(
            "freeze_strategy"
        )
    )

    selected_backbone_freeze_documented = (
        isinstance(
            freeze_strategy,
            dict
        )
        and bool(
            freeze_strategy.get(
                "frozen_layers"
            )
        )
    )

    metrics_tied = all(
        math.isclose(
            float(
                transfer_metrics[
                    metric
                ]
            ),
            float(
                baseline_metrics[
                    metric
                ]
            ),
            abs_tol=1e-12
        )
        for metric in required_metrics
    )

    transfer_advantage_observed = (
        observed_difference > 0
        and not metrics_tied
    )

    # Even a positive validation delta alone
    # would not establish a causal transfer
    # advantage.
    causal_transfer_advantage_established = False

    return {
        "target_crop":
            "bell_pepper",

        "adaptation_source":
            "GREENPULSE_TOMATO_CLASSIFIER",

        "baseline_source":
            "GENERIC_IMAGENET_PRETRAINED_YOLO11N_CLS",

        "transfer_checkpoint_sha256":
            transfer_hash,

        "baseline_checkpoint_sha256":
            baseline_hash,

        "validation_images":
            comparison[
                "validation_images"
            ],

        "validation_leaf_groups":
            comparison[
                "validation_leaf_groups"
            ],

        "transfer_validation_metrics":
            transfer_metrics,

        "baseline_validation_metrics":
            baseline_metrics,

        "observed_macro_f1_difference":
            observed_difference,

        "validation_metrics_tied":
            metrics_tied,

        "transfer_advantage_observed":
            transfer_advantage_observed,

        "causal_transfer_advantage_established":
            causal_transfer_advantage_established,

        "selected_backbone_freeze_documented":
            selected_backbone_freeze_documented,

        "current_pepper_experiment_method":
            (
                "DOCUMENTED_FROZEN_BACKBONE"
                if selected_backbone_freeze_documented
                else
                "SOURCE_INITIALIZED_FINE_TUNING_"
                "WITHOUT_DOCUMENTED_BACKBONE_FREEZE"
            ),

        "frozen_backbone_protocol_fully_satisfied":
            selected_backbone_freeze_documented,

        "final_test_accuracy":
            _finite_metric(
                final_test[
                    "metrics"
                ]["accuracy"],
                "FINAL_TEST_ACCURACY"
            ),

        "final_test_macro_f1":
            _finite_metric(
                final_test[
                    "metrics"
                ]["macro_f1"],
                "FINAL_TEST_MACRO_F1"
            ),

        "final_test_errors":
            int(
                final_test[
                    "error_analysis"
                ]["total_errors"]
            ),

        "test_used_for_model_selection":
            False,

        "future_crop_protocol_requires_"
        "predeclared_freeze_strategy":
            True,

        "real_greenhouse_generalization_verified":
            False,

        "water_stress_adaptation_verified":
            False,

        "operational_release_authorized":
            False,

        "physical_actuation_allowed":
            False
    }
