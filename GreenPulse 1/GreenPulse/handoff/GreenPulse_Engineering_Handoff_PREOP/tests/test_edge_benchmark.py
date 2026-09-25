import csv
import tempfile
import time
import unittest
from pathlib import Path

from src.edge_benchmark import (
    CSV_FIELDS,
    REQUIRED_STAGES,
    SCHEMA_VERSION,
    benchmark_readiness,
    build_external_measurement,
    export_benchmark_csv,
    export_jury_summary,
    measure_stage,
)


class TestEdgeBenchmark(
    unittest.TestCase
):

    def test_schema_version(self):

        self.assertEqual(
            SCHEMA_VERSION,
            "greenpulse.edge_benchmark.v1",
        )


    def test_required_stages(self):

        self.assertEqual(
            REQUIRED_STAGES,
            (
                "preprocessing",
                "hailo_inference",
                "postprocessing",
                "fusion",
                "forecasting",
                "decision",
                "end_to_end",
                "api",
            ),
        )


    def test_measure_callable_latency(self):

        result, record = measure_stage(
            "fusion",
            lambda: 42,
        )

        self.assertEqual(
            result,
            42,
        )

        self.assertGreaterEqual(
            record[
                "latency_ms"
            ],
            0.0,
        )


    def test_measure_callable_rss(self):

        _, record = measure_stage(
            "decision",
            lambda: None,
        )

        self.assertGreater(
            record[
                "rss_before_bytes"
            ],
            0,
        )

        self.assertGreater(
            record[
                "rss_after_bytes"
            ],
            0,
        )


    def test_peak_rss_is_not_below_boundary_samples(self):

        _, record = measure_stage(
            "forecasting",
            lambda: time.sleep(
                0.01
            ),
        )

        self.assertGreaterEqual(
            record[
                "peak_process_tree_rss_bytes"
            ],
            record[
                "rss_before_bytes"
            ],
        )

        self.assertGreaterEqual(
            record[
                "peak_process_tree_rss_bytes"
            ],
            record[
                "rss_after_bytes"
            ],
        )


    def test_cpu_measurement_nonnegative(self):

        _, record = measure_stage(
            "preprocessing",
            lambda: sum(
                range(
                    1000
                )
            ),
        )

        self.assertGreaterEqual(
            record[
                "cpu_percent_equivalent"
            ],
            0.0,
        )


    def test_invalid_stage_rejected(self):

        with self.assertRaises(
            ValueError
        ):

            measure_stage(
                "training",
                lambda: None,
            )


    def test_external_hailo_measurement_preserved(self):

        record = build_external_measurement(
            stage="hailo_inference",
            latency_ms=7.5,
            measurement_source="REAL_HAILO_RUNTIME",
            runtime_target="RASPBERRY_PI_5_AI_HAT_PLUS",
            peak_process_tree_rss_bytes=500_000_000,
            cpu_percent_equivalent=30.0,
            accelerator_usage_percent=80.0,
            device_temperature_c=55.0,
        )

        self.assertEqual(
            record[
                "accelerator_usage_percent"
            ],
            80.0,
        )

        self.assertEqual(
            record[
                "device_temperature_c"
            ],
            55.0,
        )


    def test_negative_latency_rejected(self):

        with self.assertRaises(
            ValueError
        ):

            build_external_measurement(
                stage="api",
                latency_ms=-1,
                measurement_source="TEST",
                runtime_target="TEST",
            )


    def test_csv_export(self):

        row = build_external_measurement(
            stage="api",
            latency_ms=1.5,
            measurement_source="TEST",
            runtime_target="TEST",
        )


        with tempfile.TemporaryDirectory() as tmp:

            output = (
                Path(
                    tmp
                )
                / "benchmark.csv"
            )

            export_benchmark_csv(
                [
                    row
                ],
                output,
            )

            with output.open(
                "r",
                encoding="utf-8",
                newline="",
            ) as handle:

                reader = csv.DictReader(
                    handle
                )

                rows = list(
                    reader
                )


        self.assertEqual(
            tuple(
                reader.fieldnames
            ),
            CSV_FIELDS,
        )

        self.assertEqual(
            len(
                rows
            ),
            1,
        )


    def test_summary_incomplete_without_required_stages(self):

        row = build_external_measurement(
            stage="api",
            latency_ms=1.0,
            measurement_source="TEST",
            runtime_target="TEST",
        )

        readiness = benchmark_readiness(
            [
                row
            ]
        )

        self.assertFalse(
            readiness[
                "full_edge_benchmark_complete"
            ]
        )

        self.assertIn(
            "hailo_inference",
            readiness[
                "missing_stages"
            ],
        )


    def test_fake_hailo_source_cannot_complete_edge_benchmark(self):

        rows = []


        for stage in REQUIRED_STAGES:

            rows.append(
                build_external_measurement(
                    stage=stage,
                    latency_ms=1.0,
                    measurement_source="DEVELOPMENT_CALLABLE",
                    runtime_target="DESKTOP_DEVELOPMENT",
                    peak_process_tree_rss_bytes=100,
                    cpu_percent_equivalent=1.0,
                    accelerator_usage_percent=(
                        50.0
                        if stage
                        == "hailo_inference"
                        else None
                    ),
                    device_temperature_c=(
                        40.0
                        if stage
                        == "hailo_inference"
                        else None
                    ),
                )
            )


        readiness = benchmark_readiness(
            rows
        )


        self.assertFalse(
            readiness[
                "real_hailo_runtime_measured"
            ]
        )

        self.assertFalse(
            readiness[
                "full_edge_benchmark_complete"
            ]
        )


    def test_jury_summary_export(self):

        row = build_external_measurement(
            stage="api",
            latency_ms=2.0,
            measurement_source="TEST",
            runtime_target="TEST",
        )


        with tempfile.TemporaryDirectory() as tmp:

            output = (
                Path(
                    tmp
                )
                / "summary.md"
            )

            export_jury_summary(
                [
                    row
                ],
                output,
            )

            text = output.read_text(
                encoding="utf-8"
            )


        self.assertIn(
            "GreenPulse Edge Benchmark Summary",
            text,
        )

        self.assertIn(
            "Full edge benchmark complete: NO",
            text,
        )


if __name__ == "__main__":
    unittest.main()