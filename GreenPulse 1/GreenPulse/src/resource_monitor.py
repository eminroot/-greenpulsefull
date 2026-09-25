from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

import os
import statistics
import time

import psutil

from src.resource_budget import (
    RAM_LIMIT_BYTES,
    evaluate_ram_usage,
)


MONITOR_SCHEMA_VERSION = (
    "greenpulse.runtime_memory_monitor.v1"
)


def process_tree_rss_bytes(
    pid: Optional[int] = None,
) -> dict[str, Any]:

    pid = (
        os.getpid()
        if pid is None
        else pid
    )


    if (
        isinstance(
            pid,
            bool,
        )
        or not isinstance(
            pid,
            int,
        )
        or pid <= 0
    ):

        raise ValueError(
            "pid must be a positive integer."
        )


    try:

        parent = psutil.Process(
            pid
        )

    except psutil.Error as exc:

        raise RuntimeError(
            "Process is not available."
        ) from exc


    processes = [
        parent
    ]


    try:

        processes.extend(
            parent.children(
                recursive=True
            )
        )

    except psutil.Error:

        pass


    total_rss = 0
    measured_pids = []
    skipped_pids = []


    for process in processes:

        try:

            memory = (
                process.memory_info()
            )

            total_rss += int(
                memory.rss
            )

            measured_pids.append(
                process.pid
            )

        except psutil.Error:

            skipped_pids.append(
                process.pid
            )


    return {
        "pid":
            pid,

        "rss_bytes":
            total_rss,

        "measured_pids":
            sorted(
                set(
                    measured_pids
                )
            ),

        "skipped_pids":
            sorted(
                set(
                    skipped_pids
                )
            ),

        "includes_recursive_children":
            True,
    }


def summarize_memory_samples(
    samples: list[int],
) -> dict[str, Any]:

    if (
        not isinstance(
            samples,
            list,
        )
        or not samples
    ):

        raise ValueError(
            "samples must be a non-empty list."
        )


    parsed = []


    for value in samples:

        if (
            isinstance(
                value,
                bool,
            )
            or not isinstance(
                value,
                int,
            )
            or value < 0
        ):

            raise ValueError(
                "Every memory sample must be "
                "a non-negative integer."
            )

        parsed.append(
            value
        )


    peak = max(
        parsed
    )


    average = statistics.fmean(
        parsed
    )


    result = evaluate_ram_usage(
        peak
    )


    return {
        "schema_version":
            MONITOR_SCHEMA_VERSION,

        "sample_count":
            len(
                parsed
            ),

        "peak_rss_bytes":
            peak,

        "average_rss_bytes":
            round(
                average,
                3,
            ),

        "minimum_rss_bytes":
            min(
                parsed
            ),

        "ram_limit_bytes":
            RAM_LIMIT_BYTES,

        "acceptance_based_on":
            "PEAK_PROCESS_TREE_RSS",

        "within_budget":
            result[
                "within_budget"
            ],

        "status":
            result[
                "status"
            ],
    }


def run_memory_stability_monitor(
    *,
    duration_seconds: float,
    interval_seconds: float = 1.0,
    pid: Optional[int] = None,
) -> dict[str, Any]:

    if (
        isinstance(
            duration_seconds,
            bool,
        )
        or not isinstance(
            duration_seconds,
            (int, float),
        )
        or duration_seconds <= 0
    ):

        raise ValueError(
            "duration_seconds must be > 0."
        )


    if (
        isinstance(
            interval_seconds,
            bool,
        )
        or not isinstance(
            interval_seconds,
            (int, float),
        )
        or interval_seconds <= 0
    ):

        raise ValueError(
            "interval_seconds must be > 0."
        )


    if interval_seconds > duration_seconds:

        raise ValueError(
            "interval_seconds cannot exceed duration_seconds."
        )


    started_at = datetime.now(
        timezone.utc
    ).isoformat()


    started = time.monotonic()

    samples = []
    pid_sets = []


    while True:

        snapshot = process_tree_rss_bytes(
            pid=pid
        )

        samples.append(
            snapshot[
                "rss_bytes"
            ]
        )

        pid_sets.append(
            snapshot[
                "measured_pids"
            ]
        )


        elapsed = (
            time.monotonic()
            - started
        )


        if elapsed >= duration_seconds:

            break


        remaining = (
            duration_seconds
            - elapsed
        )

        time.sleep(
            min(
                interval_seconds,
                remaining,
            )
        )


    finished_at = datetime.now(
        timezone.utc
    ).isoformat()


    summary = summarize_memory_samples(
        samples
    )


    return {
        **summary,

        "started_at_utc":
            started_at,

        "finished_at_utc":
            finished_at,

        "requested_duration_seconds":
            float(
                duration_seconds
            ),

        "interval_seconds":
            float(
                interval_seconds
            ),

        "samples_rss_bytes":
            samples,

        "observed_pid_sets":
            pid_sets,

        "measurement_scope":
            (
                "PROCESS_PLUS_RECURSIVE_CHILDREN"
            ),

        "system_wide_ram_measured":
            False,

        "gpu_memory_measured":
            False,

        "hailo_memory_measured":
            False,

        "raspberry_pi_5_measured":
            False,
    }