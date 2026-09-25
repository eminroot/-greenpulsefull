from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

import csv
import math
import os
import threading
import time

import psutil

from src.resource_monitor import (
    process_tree_rss_bytes,
)


SCHEMA_VERSION = (
    "greenpulse.edge_benchmark.v1"
)


REQUIRED_STAGES = (
    "preprocessing",
    "hailo_inference",
    "postprocessing",
    "fusion",
    "forecasting",
    "decision",
    "end_to_end",
    "api",
)


CSV_FIELDS = (
    "schema_version",
    "stage",
    "measured",
    "measurement_source",
    "runtime_target",
    "latency_ms",
    "rss_before_bytes",
    "rss_after_bytes",
    "peak_process_tree_rss_bytes",
    "cpu_percent_equivalent",
    "accelerator_usage_percent",
    "device_temperature_c",
    "notes",
)


def _finite_nonnegative(
    value: Any,
    name: str,
    *,
    allow_none: bool = False,
) -> Optional[float]:

    if value is None:

        if allow_none:

            return None

        raise ValueError(
            f"{name} is required."
        )


    if (
        isinstance(
            value,
            bool,
        )
        or not isinstance(
            value,
            (int, float),
        )
    ):

        raise ValueError(
            f"{name} must be numeric."
        )


    parsed = float(
        value
    )


    if (
        not math.isfinite(
            parsed
        )
        or parsed < 0
    ):

        raise ValueError(
            f"{name} must be finite and non-negative."
        )


    return parsed


def _validate_stage(
    stage: str,
) -> str:

    if (
        not isinstance(
            stage,
            str,
        )
        or stage
        not in REQUIRED_STAGES
    ):

        raise ValueError(
            f"Unsupported benchmark stage: {stage!r}"
        )


    return stage


def _process_tree_cpu_seconds(
    pid: Optional[int] = None,
) -> float:

    root_pid = (
        os.getpid()
        if pid is None
        else int(
            pid
        )
    )


    try:

        parent = psutil.Process(
            root_pid
        )

    except (
        psutil.NoSuchProcess,
        psutil.AccessDenied,
    ):

        return 0.0


    processes = [
        parent
    ]


    try:

        processes.extend(
            parent.children(
                recursive=True
            )
        )

    except (
        psutil.NoSuchProcess,
        psutil.AccessDenied,
    ):

        pass


    total = 0.0


    for process in processes:

        try:

            cpu = process.cpu_times()

            total += (
                float(
                    cpu.user
                )
                + float(
                    cpu.system
                )
            )

        except (
            psutil.NoSuchProcess,
            psutil.AccessDenied,
        ):

            continue


    return total


class _PeakRssSampler:

    def __init__(
        self,
        *,
        pid: Optional[int] = None,
        interval_seconds: float = 0.01,
    ):

        if interval_seconds <= 0:

            raise ValueError(
                "interval_seconds must be positive."
            )


        self.pid = pid
        self.interval_seconds = float(
            interval_seconds
        )

        self.peak_bytes = 0

        self._stop = threading.Event()

        self._thread = threading.Thread(
            target=self._run,
            daemon=True,
        )


    def _sample(self) -> None:

        try:

            sample = process_tree_rss_bytes(
                self.pid
            )

            value = int(
                sample[
                    "rss_bytes"
                ]
            )

            self.peak_bytes = max(
                self.peak_bytes,
                value,
            )

        except Exception:

            pass


    def _run(self) -> None:

        self._sample()


        while not self._stop.wait(
            self.interval_seconds
        ):

            self._sample()


    def start(self) -> None:

        self._sample()

        self._thread.start()


    def stop(self) -> int:

        self._stop.set()

        self._thread.join(
            timeout=2
        )

        self._sample()

        return int(
            self.peak_bytes
        )


def measure_stage(
    stage: str,
    function: Callable[..., Any],
    *args: Any,
    measurement_source: str = "DEVELOPMENT_CALLABLE",
    runtime_target: str = "DESKTOP_DEVELOPMENT",
    notes: str = "",
    **kwargs: Any,
) -> tuple[Any, dict[str, Any]]:

    stage = _validate_stage(
        stage
    )


    if not callable(
        function
    ):

        raise ValueError(
            "function must be callable."
        )


    if (
        not isinstance(
            measurement_source,
            str,
        )
        or not measurement_source.strip()
    ):

        raise ValueError(
            "measurement_source is required."
        )


    if (
        not isinstance(
            runtime_target,
            str,
        )
        or not runtime_target.strip()
    ):

        raise ValueError(
            "runtime_target is required."
        )


    rss_before = int(
        process_tree_rss_bytes()[
            "rss_bytes"
        ]
    )

    cpu_before = (
        _process_tree_cpu_seconds()
    )

    peak_sampler = _PeakRssSampler()

    peak_sampler.start()


    started = time.perf_counter_ns()


    try:

        result = function(
            *args,
            **kwargs,
        )

    finally:

        finished = time.perf_counter_ns()

        peak_rss = peak_sampler.stop()


    rss_after = int(
        process_tree_rss_bytes()[
            "rss_bytes"
        ]
    )

    cpu_after = (
        _process_tree_cpu_seconds()
    )


    latency_ms = (
        finished
        - started
    ) / 1_000_000.0


    wall_seconds = max(
        (
            finished
            - started
        )
        / 1_000_000_000.0,
        1e-12,
    )


    cpu_delta = max(
        0.0,
        cpu_after
        - cpu_before,
    )


    cpu_percent_equivalent = (
        cpu_delta
        / wall_seconds
        * 100.0
    )


    peak_rss = max(
        int(
            peak_rss
        ),
        rss_before,
        rss_after,
    )


    record = {
        "schema_version":
            SCHEMA_VERSION,

        "stage":
            stage,

        "measured":
            True,

        "measurement_source":
            measurement_source,

        "runtime_target":
            runtime_target,

        "latency_ms":
            float(
                latency_ms
            ),

        "rss_before_bytes":
            rss_before,

        "rss_after_bytes":
            rss_after,

        "peak_process_tree_rss_bytes":
            peak_rss,

        "cpu_percent_equivalent":
            float(
                cpu_percent_equivalent
            ),

        "accelerator_usage_percent":
            None,

        "device_temperature_c":
            None,

        "notes":
            str(
                notes
            ),
    }


    return (
        result,
        record,
    )


def build_external_measurement(
    *,
    stage: str,
    latency_ms: float,
    measurement_source: str,
    runtime_target: str,
    rss_before_bytes: Optional[int] = None,
    rss_after_bytes: Optional[int] = None,
    peak_process_tree_rss_bytes: Optional[int] = None,
    cpu_percent_equivalent: Optional[float] = None,
    accelerator_usage_percent: Optional[float] = None,
    device_temperature_c: Optional[float] = None,
    notes: str = "",
) -> dict[str, Any]:

    stage = _validate_stage(
        stage
    )


    latency = _finite_nonnegative(
        latency_ms,
        "latency_ms",
    )


    if (
        not isinstance(
            measurement_source,
            str,
        )
        or not measurement_source.strip()
    ):

        raise ValueError(
            "measurement_source is required."
        )


    if (
        not isinstance(
            runtime_target,
            str,
        )
        or not runtime_target.strip()
    ):

        raise ValueError(
            "runtime_target is required."
        )


    def optional_int(
        value,
        name,
    ):

        parsed = _finite_nonnegative(
            value,
            name,
            allow_none=True,
        )

        return (
            None
            if parsed is None
            else int(
                parsed
            )
        )


    return {
        "schema_version":
            SCHEMA_VERSION,

        "stage":
            stage,

        "measured":
            True,

        "measurement_source":
            measurement_source,

        "runtime_target":
            runtime_target,

        "latency_ms":
            latency,

        "rss_before_bytes":
            optional_int(
                rss_before_bytes,
                "rss_before_bytes",
            ),

        "rss_after_bytes":
            optional_int(
                rss_after_bytes,
                "rss_after_bytes",
            ),

        "peak_process_tree_rss_bytes":
            optional_int(
                peak_process_tree_rss_bytes,
                "peak_process_tree_rss_bytes",
            ),

        "cpu_percent_equivalent":
            _finite_nonnegative(
                cpu_percent_equivalent,
                "cpu_percent_equivalent",
                allow_none=True,
            ),

        "accelerator_usage_percent":
            _finite_nonnegative(
                accelerator_usage_percent,
                "accelerator_usage_percent",
                allow_none=True,
            ),

        "device_temperature_c":
            _finite_nonnegative(
                device_temperature_c,
                "device_temperature_c",
                allow_none=True,
            ),

        "notes":
            str(
                notes
            ),
    }


def benchmark_readiness(
    records: Iterable[
        dict[str, Any]
    ],
) -> dict[str, Any]:

    rows = list(
        records
    )


    measured_stages = {
        row.get(
            "stage"
        )
        for row in rows
        if row.get(
            "measured"
        )
        is True
    }


    missing_stages = [
        stage
        for stage in REQUIRED_STAGES
        if stage
        not in measured_stages
    ]


    hailo_rows = [
        row
        for row in rows
        if (
            row.get(
                "stage"
            )
            == "hailo_inference"
            and row.get(
                "measured"
            )
            is True
        )
    ]


    real_hailo = any(
        row.get(
            "measurement_source"
        )
        == "REAL_HAILO_RUNTIME"
        and row.get(
            "runtime_target"
        )
        == "RASPBERRY_PI_5_AI_HAT_PLUS"
        for row in hailo_rows
    )


    accelerator_measured = any(
        row.get(
            "accelerator_usage_percent"
        )
        is not None
        for row in rows
    )


    temperature_measured = any(
        row.get(
            "device_temperature_c"
        )
        is not None
        for row in rows
    )


    peak_ram_measured = any(
        row.get(
            "peak_process_tree_rss_bytes"
        )
        is not None
        for row in rows
    )


    cpu_measured = any(
        row.get(
            "cpu_percent_equivalent"
        )
        is not None
        for row in rows
    )


    api_measured = (
        "api"
        in measured_stages
    )


    full_edge_benchmark_complete = all(
        (
            not missing_stages,
            real_hailo,
            accelerator_measured,
            temperature_measured,
            peak_ram_measured,
            cpu_measured,
            api_measured,
        )
    )


    return {
        "schema_version":
            SCHEMA_VERSION,

        "required_stages":
            list(
                REQUIRED_STAGES
            ),

        "measured_stages":
            sorted(
                measured_stages
            ),

        "missing_stages":
            missing_stages,

        "real_hailo_runtime_measured":
            real_hailo,

        "accelerator_usage_measured":
            accelerator_measured,

        "device_temperature_measured":
            temperature_measured,

        "peak_ram_measured":
            peak_ram_measured,

        "cpu_measured":
            cpu_measured,

        "api_latency_measured":
            api_measured,

        "full_edge_benchmark_complete":
            full_edge_benchmark_complete,
    }


def export_benchmark_csv(
    records: Iterable[
        dict[str, Any]
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


    rows = list(
        records
    )


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
                    for field in CSV_FIELDS
                }
            )


    return output


def export_jury_summary(
    records: Iterable[
        dict[str, Any]
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


    rows = list(
        records
    )

    readiness = benchmark_readiness(
        rows
    )


    lines = [
        "# GreenPulse Edge Benchmark Summary",
        "",
        "| Stage | Latency (ms) | Peak RSS (bytes) | CPU % eq. | Accelerator % | Temp C | Source | Target |",
        "|---|---:|---:|---:|---:|---:|---|---|",
    ]


    for row in rows:

        lines.append(
            "| {stage} | {latency} | {peak} | {cpu} | {accel} | {temp} | {source} | {target} |".format(
                stage=row.get(
                    "stage"
                ),
                latency=row.get(
                    "latency_ms"
                ),
                peak=row.get(
                    "peak_process_tree_rss_bytes"
                ),
                cpu=row.get(
                    "cpu_percent_equivalent"
                ),
                accel=row.get(
                    "accelerator_usage_percent"
                ),
                temp=row.get(
                    "device_temperature_c"
                ),
                source=row.get(
                    "measurement_source"
                ),
                target=row.get(
                    "runtime_target"
                ),
            )
        )


    lines.extend(
        [
            "",
            "## Readiness",
            "",
            (
                "- Full edge benchmark complete: "
                + (
                    "YES"
                    if readiness[
                        "full_edge_benchmark_complete"
                    ]
                    else "NO"
                )
            ),
            (
                "- Real Hailo runtime measured: "
                + (
                    "YES"
                    if readiness[
                        "real_hailo_runtime_measured"
                    ]
                    else "NO"
                )
            ),
            (
                "- Missing stages: "
                + (
                    ", ".join(
                        readiness[
                            "missing_stages"
                        ]
                    )
                    if readiness[
                        "missing_stages"
                    ]
                    else "NONE"
                )
            ),
            "",
        ]
    )


    output.write_text(
        "\n".join(
            lines
        ),
        encoding="utf-8",
    )


    return output