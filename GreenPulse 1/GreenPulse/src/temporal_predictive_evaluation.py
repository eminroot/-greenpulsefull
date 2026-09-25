from __future__ import annotations

from math import sqrt
from typing import Any, Sequence


SCHEMA_VERSION = (
    "greenpulse.temporal_predictive_evaluation.v1"
)

SYNTHETIC_SCOPE = (
    "SYNTHETIC_TEST_FIXTURE"
)

REAL_SCOPE = (
    "REAL_VALIDATED_TEMPORAL_DATASET"
)


def _binary_vector(
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


def _numeric_vector(
    values: Sequence[float],
    name: str,
) -> list[float]:

    result = [
        float(value)
        for value in values
    ]

    if not result:
        raise ValueError(
            f"{name} must not be empty."
        )

    return result


def binary_metrics(
    y_true: Sequence[int],
    y_pred: Sequence[int],
) -> dict[str, float | int]:

    truth = _binary_vector(
        y_true,
        "y_true",
    )

    pred = _binary_vector(
        y_pred,
        "y_pred",
    )

    if len(truth) != len(pred):
        raise ValueError(
            "Binary vector length mismatch."
        )

    tp = sum(
        t == 1 and p == 1
        for t, p in zip(truth, pred)
    )

    tn = sum(
        t == 0 and p == 0
        for t, p in zip(truth, pred)
    )

    fp = sum(
        t == 0 and p == 1
        for t, p in zip(truth, pred)
    )

    fn = sum(
        t == 1 and p == 0
        for t, p in zip(truth, pred)
    )

    precision = (
        tp / (tp + fp)
        if tp + fp
        else 0.0
    )

    recall = (
        tp / (tp + fn)
        if tp + fn
        else 0.0
    )

    f1 = (
        2 * precision * recall
        / (precision + recall)
        if precision + recall
        else 0.0
    )

    fpr = (
        fp / (fp + tn)
        if fp + tn
        else 0.0
    )

    fnr = (
        fn / (fn + tp)
        if fn + tp
        else 0.0
    )

    return {
        "tp": tp,
        "tn": tn,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_positive_rate": fpr,
        "false_negative_rate": fnr,
    }


def regression_metrics(
    y_true: Sequence[float],
    y_pred: Sequence[float],
) -> dict[str, float]:

    truth = _numeric_vector(
        y_true,
        "y_true",
    )

    pred = _numeric_vector(
        y_pred,
        "y_pred",
    )

    if len(truth) != len(pred):
        raise ValueError(
            "Regression vector length mismatch."
        )

    errors = [
        prediction - target
        for target, prediction
        in zip(truth, pred)
    ]

    mae = sum(
        abs(error)
        for error in errors
    ) / len(errors)

    rmse = sqrt(
        sum(
            error ** 2
            for error in errors
        )
        / len(errors)
    )

    return {
        "mae": mae,
        "rmse": rmse,
    }


def compare_single_frame_vs_temporal(
    *,
    y_true: Sequence[int],
    single_frame: Sequence[int],
    temporal_verified: Sequence[int],
) -> dict[str, Any]:

    single = binary_metrics(
        y_true,
        single_frame,
    )

    temporal = binary_metrics(
        y_true,
        temporal_verified,
    )

    return {
        "single_frame":
            single,

        "temporal_verified":
            temporal,

        "delta": {
            "f1":
                temporal["f1"]
                - single["f1"],

            "false_positive_rate":
                temporal[
                    "false_positive_rate"
                ]
                - single[
                    "false_positive_rate"
                ],

            "false_negative_rate":
                temporal[
                    "false_negative_rate"
                ]
                - single[
                    "false_negative_rate"
                ],
        },

        "temporal_f1_not_worse":
            (
                temporal["f1"]
                >= single["f1"]
            ),
    }


def compare_forecast_vs_naive(
    *,
    y_true: Sequence[float],
    forecast: Sequence[float],
    naive: Sequence[float],
) -> dict[str, Any]:

    forecast_metrics = regression_metrics(
        y_true,
        forecast,
    )

    naive_metrics = regression_metrics(
        y_true,
        naive,
    )

    better = (
        forecast_metrics["mae"]
        < naive_metrics["mae"]
        and forecast_metrics["rmse"]
        < naive_metrics["rmse"]
    )

    return {
        "forecast":
            forecast_metrics,

        "naive_baseline":
            naive_metrics,

        "forecast_better_than_naive":
            better,

        "mae_improvement":
            (
                naive_metrics["mae"]
                - forecast_metrics["mae"]
            ),

        "rmse_improvement":
            (
                naive_metrics["rmse"]
                - forecast_metrics["rmse"]
            ),
    }


def evaluate_alert_lead_time(
    *,
    event_flags: Sequence[int],
    forecast_alerts: Sequence[int],
    step_minutes: float,
    action_window_steps: int,
) -> dict[str, Any]:

    events = _binary_vector(
        event_flags,
        "event_flags",
    )

    alerts = _binary_vector(
        forecast_alerts,
        "forecast_alerts",
    )

    if len(events) != len(alerts):
        raise ValueError(
            "Event/alert length mismatch."
        )

    if step_minutes <= 0:
        raise ValueError(
            "step_minutes must be positive."
        )

    if action_window_steps < 1:
        raise ValueError(
            "action_window_steps must be >= 1."
        )

    lead_times = []
    false_alerts = 0
    total_alerts = sum(alerts)

    for index, alert in enumerate(alerts):

        if alert != 1:
            continue

        end = min(
            len(events),
            index
            + action_window_steps
            + 1,
        )

        matching_event = None

        for event_index in range(
            index,
            end,
        ):
            if events[event_index] == 1:
                matching_event = event_index
                break

        if matching_event is None:
            false_alerts += 1
        else:
            lead_times.append(
                (
                    matching_event
                    - index
                )
                * step_minutes
            )

    false_alarm_rate = (
        false_alerts / total_alerts
        if total_alerts
        else 0.0
    )

    positive_lead_times = [
        value
        for value in lead_times
        if value > 0
    ]

    return {
        "total_alerts":
            total_alerts,

        "matched_alerts":
            len(lead_times),

        "false_alerts":
            false_alerts,

        "false_alarm_rate":
            false_alarm_rate,

        "lead_times_minutes":
            lead_times,

        "positive_lead_time_count":
            len(
                positive_lead_times
            ),

        "mean_positive_lead_time_minutes":
            (
                sum(positive_lead_times)
                / len(positive_lead_times)
                if positive_lead_times
                else 0.0
            ),
    }


def evaluate_temporal_predictive_system(
    *,
    decision_truth: Sequence[int],
    single_frame_decisions: Sequence[int],
    temporal_decisions: Sequence[int],
    forecast_truth: Sequence[float],
    forecast_predictions: Sequence[float],
    naive_predictions: Sequence[float],
    event_flags: Sequence[int],
    forecast_alerts: Sequence[int],
    step_minutes: float,
    action_window_steps: int,
    max_false_alarm_rate: float,
    evidence_scope: str,
) -> dict[str, Any]:

    if evidence_scope not in {
        SYNTHETIC_SCOPE,
        REAL_SCOPE,
    }:
        raise ValueError(
            "Unsupported evidence_scope."
        )

    if not (
        0.0
        <= max_false_alarm_rate
        <= 1.0
    ):
        raise ValueError(
            "max_false_alarm_rate must be within [0,1]."
        )

    temporal = (
        compare_single_frame_vs_temporal(
            y_true=decision_truth,
            single_frame=single_frame_decisions,
            temporal_verified=temporal_decisions,
        )
    )

    forecast = (
        compare_forecast_vs_naive(
            y_true=forecast_truth,
            forecast=forecast_predictions,
            naive=naive_predictions,
        )
    )

    lead_time = (
        evaluate_alert_lead_time(
            event_flags=event_flags,
            forecast_alerts=forecast_alerts,
            step_minutes=step_minutes,
            action_window_steps=action_window_steps,
        )
    )

    acceptable_false_alarms = (
        lead_time[
            "false_alarm_rate"
        ]
        <= max_false_alarm_rate
    )

    actionable_lead_time = (
        lead_time[
            "mean_positive_lead_time_minutes"
        ]
        > 0.0
    )

    benefit_measured = all(
        (
            temporal[
                "temporal_f1_not_worse"
            ],
            forecast[
                "forecast_better_than_naive"
            ],
            actionable_lead_time,
            acceptable_false_alarms,
        )
    )

    claim_permitted = (
        evidence_scope == REAL_SCOPE
        and benefit_measured
    )

    return {
        "schema_version":
            SCHEMA_VERSION,

        "evidence_scope":
            evidence_scope,

        "single_frame_vs_temporal":
            temporal,

        "forecast_vs_naive":
            forecast,

        "lead_time":
            lead_time,

        "acceptance": {
            "max_false_alarm_rate":
                max_false_alarm_rate,

            "false_alarm_rate_acceptable":
                acceptable_false_alarms,

            "actionable_positive_lead_time":
                actionable_lead_time,

            "measured_conditions_satisfied":
                benefit_measured,
        },

        "claim_boundary": {
            "real_dataset_used":
                evidence_scope
                == REAL_SCOPE,

            "forecast_benefit_claim_permitted":
                claim_permitted,

            "synthetic_result_may_be_claimed_real":
                False,
        },
    }