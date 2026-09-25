from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Optional

import csv
import math
import os

from src.resource_budget import (
    RAM_LIMIT_BYTES,
    evaluate_ram_usage,
)

from src.resource_monitor import (
    process_tree_rss_bytes,
)


SCHEMA_VERSION = (
    "greenpulse.long_run_stability.v1"
)


FINAL_RUNTIME_TARGET = (
    "RASPBERRY_PI_5_AI_HAT_PLUS"
)


CSV_FIELDS = (
    "sample_index",
    "elapsed_seconds",
    "rss_bytes",
    "ram_budget_pass",
    "db_size_bytes",
    "model_status",
    "api_status",
    "camera_status",
    "sensor_status",
)


def classify_duration(
    duration_seconds: Any,
) -> str:

    if (
        isinstance(
            duration_seconds,
            bool,
        )
        or not isinstance(
            duration_seconds,
            (int, float),
        )
    ):

        raise ValueError(
            "duration_seconds must be numeric."
        )


    duration = float(
        duration_seconds
    )


    if (
        not math.isfinite(
            duration
        )
        or duration <= 0
    ):

        raise ValueError(
            "duration_seconds must be positive."
        )


    if duration == 1800:

        return "30_MINUTE"


    if duration == 3600:

        return "1_HOUR"


    # Implementation convention:
    # "multi-hour" means at least 2 hours.
    if duration >= 7200:

        return "MULTI_HOUR"


    return "CUSTOM"


def _run_probe(
    probe: Optional[
        Callable[
            [],
            Any,
        ]
    ],
    *,
    exception_status: str,
) -> str:

    if probe is None:

        return "NOT_CONFIGURED"


    try:

        result = probe()

    except Exception:

        return exception_status


    if isinstance(
        result,
        bool,
    ):

        return (
            "OK"
            if result
            else exception_status
        )


    if (
        not isinstance(
            result,
            str,
        )
        or not result.strip()
    ):

        return "INVALID_PROBE_RESULT"


    return result.strip().upper()


def capture_stability_sample(
    *,
    sample_index: int,
    elapsed_seconds: float,
    db_path: Optional[Any] = None,
    pid: Optional[int] = None,
    model_probe: Optional[
        Callable[
            [],
            Any,
        ]
    ] = None,
    api_probe: Optional[
        Callable[
            [],
            Any,
        ]
    ] = None,
    camera_probe: Optional[
        Callable[
            [],
            Any,
        ]
    ] = None,
    sensor_probe: Optional[
        Callable[
            [],
            Any,
        ]
    ] = None,
) -> dict[str, Any]:

    if (
        type(
            sample_index
        )
        is not int
        or sample_index < 0
    ):

        raise ValueError(
            "sample_index must be a non-negative integer."
        )


    if (
        isinstance(
            elapsed_seconds,
            bool,
        )
        or not isinstance(
            elapsed_seconds,
            (int, float),
        )
    ):

        raise ValueError(
            "elapsed_seconds must be numeric."
        )


    elapsed = float(
        elapsed_seconds
    )


    if (
        not math.isfinite(
            elapsed
        )
        or elapsed < 0
    ):

        raise ValueError(
            "elapsed_seconds must be finite and non-negative."
        )


    rss_result = process_tree_rss_bytes(
        pid
    )

    rss_bytes = int(
        rss_result[
            "rss_bytes"
        ]
    )

    budget = evaluate_ram_usage(
        rss_bytes
    )


    database_size = None


    if db_path is not None:

        db = Path(
            db_path
        )


        if db.is_file():

            database_size = int(
                db.stat().st_size
            )


    model_status = _run_probe(
        model_probe,
        exception_status="CRASH",
    )

    api_status = _run_probe(
        api_probe,
        exception_status="CRASH",
    )

    camera_status = _run_probe(
        camera_probe,
        exception_status="PROBE_ERROR",
    )

    sensor_status = _run_probe(
        sensor_probe,
        exception_status="PROBE_ERROR",
    )


    return {
        "schema_version":
            SCHEMA_VERSION,

        "sample_index":
            sample_index,

        "elapsed_seconds":
            elapsed,

        "pid":
            (
                os.getpid()
                if pid is None
                else int(
                    pid
                )
            ),

        "rss_bytes":
            rss_bytes,

        "ram_budget_pass":
            bool(
                budget[
                    "within_budget"
                ]
            ),

        "ram_limit_bytes":
            RAM_LIMIT_BYTES,

        "db_size_bytes":
            database_size,

        "model_status":
            model_status,

        "api_status":
            api_status,

        "camera_status":
            camera_status,

        "sensor_status":
            sensor_status,

        "rss_measurement": {
            "measured_pids":
                list(
                    rss_result[
                        "measured_pids"
                    ]
                ),

            "skipped_pids":
                list(
                    rss_result[
                        "skipped_pids"
                    ]
                ),

            "includes_recursive_children":
                bool(
                    rss_result[
                        "includes_recursive_children"
                    ]
                ),
        },
    }


def summarize_stability_samples(
    samples: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
    *,
    requested_duration_seconds: float,
    runtime_target: str,
    real_hailo_runtime: bool = False,
) -> dict[str, Any]:

    rows = [
        dict(
            sample
        )
        for sample in samples
    ]


    if not rows:

        raise ValueError(
            "At least one stability sample is required."
        )


    duration_class = classify_duration(
        requested_duration_seconds
    )


    rss_values = [
        int(
            row[
                "rss_bytes"
            ]
        )
        for row in rows
    ]


    elapsed_values = [
        float(
            row[
                "elapsed_seconds"
            ]
        )
        for row in rows
    ]


    db_values = [
        int(
            row[
                "db_size_bytes"
            ]
        )
        for row in rows
        if row.get(
            "db_size_bytes"
        )
        is not None
    ]


    peak_rss = max(
        rss_values
    )

    min_rss = min(
        rss_values
    )

    first_rss = rss_values[
        0
    ]

    last_rss = rss_values[
        -1
    ]

    rss_growth = (
        last_rss
        - first_rss
    )


    all_ram_below_limit = all(
        int(
            value
        )
        < RAM_LIMIT_BYTES
        for value in rss_values
    )


    observed_elapsed = max(
        elapsed_values
    )


    duration_requirement_met = (
        observed_elapsed
        >= float(
            requested_duration_seconds
        )
    )


    model_crashes = sum(
        row.get(
            "model_status"
        )
        == "CRASH"
        for row in rows
    )

    api_crashes = sum(
        row.get(
            "api_status"
        )
        == "CRASH"
        for row in rows
    )

    camera_timeouts = sum(
        row.get(
            "camera_status"
        )
        == "TIMEOUT"
        for row in rows
    )

    sensor_timeouts = sum(
        row.get(
            "sensor_status"
        )
        == "TIMEOUT"
        for row in rows
    )


    db_growth = None


    if len(
        db_values
    ) >= 2:

        db_growth = (
            db_values[
                -1
            ]
            - db_values[
                0
            ]
        )


    # This is an observation flag only.
    # Positive RSS growth does NOT prove a memory leak.
    increasing_ram_observed = (
        rss_growth > 0
    )


    memory_leak_confirmed = False


    final_release_memory_criterion_met = all(
        (
            duration_requirement_met,
            all_ram_below_limit,
            runtime_target
            == FINAL_RUNTIME_TARGET,
            real_hailo_runtime
            is True,
        )
    )


    return {
        "schema_version":
            SCHEMA_VERSION,

        "requested_duration_seconds":
            float(
                requested_duration_seconds
            ),

        "duration_class":
            duration_class,

        "observed_elapsed_seconds":
            observed_elapsed,

        "duration_requirement_met":
            duration_requirement_met,

        "runtime_target":
            runtime_target,

        "sample_count":
            len(
                rows
            ),

        "min_rss_bytes":
            min_rss,

        "peak_rss_bytes":
            peak_rss,

        "first_rss_bytes":
            first_rss,

        "last_rss_bytes":
            last_rss,

        "rss_growth_bytes":
            rss_growth,

        "increasing_ram_observed":
            increasing_ram_observed,

        "memory_leak_confirmed":
            memory_leak_confirmed,

        "all_ram_below_hard_limit":
            all_ram_below_limit,

        "hard_ram_limit_bytes":
            RAM_LIMIT_BYTES,

        "model_crash_count":
            model_crashes,

        "api_crash_count":
            api_crashes,

        "camera_timeout_count":
            camera_timeouts,

        "sensor_timeout_count":
            sensor_timeouts,

        "db_growth_bytes":
            db_growth,

        "real_hailo_runtime":
            bool(
                real_hailo_runtime
            ),

        "final_release_memory_criterion_met":
            final_release_memory_criterion_met,

        "scientific_guardrails": {
            "positive_rss_growth_equals_memory_leak":
                False,

            "short_test_equals_30_minute_stability":
                False,

            "desktop_runtime_equals_pi5_hailo_runtime":
                False,

            "unit_test_equals_long_run_validation":
                False,
        },
    }


def export_stability_csv(
    samples: Iterable[
        Mapping[
            str,
            Any,
        ]
    ],
    path: Any,
) -> Path:

    output = Path(
        path
    )


    if output.exists():

        raise FileExistsError(
            f"Output already exists: {output}"
        )


    if not output.parent.is_dir():

        raise FileNotFoundError(
            "Output directory does not exist."
        )


    rows = [
        dict(
            sample
        )
        for sample in samples
    ]


    with output.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as handle:

        writer = csv.DictWriter(
            handle,
            fieldnames=CSV_FIELDS,
            extrasaction="ignore",
        )

        writer.writeheader()


        for row in rows:

            writer.writerow(
                {
                    field:
                        row.get(
                            field
                        )
                    for field
                    in CSV_FIELDS
                }
            )


    return output