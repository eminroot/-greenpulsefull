import csv
import tempfile
import unittest
from pathlib import Path

from src.long_run_stability import (
    CSV_FIELDS,
    FINAL_RUNTIME_TARGET,
    SCHEMA_VERSION,
    capture_stability_sample,
    classify_duration,
    export_stability_csv,
    summarize_stability_samples,
)


def fake_sample(
    index,
    elapsed,
    rss,
    *,
    db_size=100,
    model="OK",
    api="OK",
    camera="OK",
    sensor="OK",
):

    return {
        "schema_version":
            SCHEMA_VERSION,

        "sample_index":
            index,

        "elapsed_seconds":
            float(
                elapsed
            ),

        "rss_bytes":
            int(
                rss
            ),

        "ram_budget_pass":
            rss
            < 3_000_000_000,

        "db_size_bytes":
            db_size,

        "model_status":
            model,

        "api_status":
            api,

        "camera_status":
            camera,

        "sensor_status":
            sensor,
    }


class TestLongRunStability(
    unittest.TestCase
):

    def test_schema_version(self):

        self.assertEqual(
            SCHEMA_VERSION,
            "greenpulse.long_run_stability.v1",
        )


    def test_30_minute_classification(self):

        self.assertEqual(
            classify_duration(
                1800
            ),
            "30_MINUTE",
        )


    def test_one_hour_classification(self):

        self.assertEqual(
            classify_duration(
                3600
            ),
            "1_HOUR",
        )


    def test_multi_hour_classification(self):

        self.assertEqual(
            classify_duration(
                7200
            ),
            "MULTI_HOUR",
        )


    def test_short_custom_duration_not_promoted(self):

        self.assertEqual(
            classify_duration(
                60
            ),
            "CUSTOM",
        )


    def test_runtime_sample_captures_rss(self):

        sample = capture_stability_sample(
            sample_index=0,
            elapsed_seconds=0,
        )

        self.assertGreater(
            sample[
                "rss_bytes"
            ],
            0,
        )


    def test_runtime_sample_reads_db_size_without_writing(self):

        with tempfile.TemporaryDirectory() as tmp:

            db = Path(tmp) / "test.db"

            db.write_bytes(
                b"123456"
            )

            before = db.read_bytes()

            sample = capture_stability_sample(
                sample_index=0,
                elapsed_seconds=0,
                db_path=db,
            )

            after = db.read_bytes()


        self.assertEqual(
            sample[
                "db_size_bytes"
            ],
            6,
        )

        self.assertEqual(
            before,
            after,
        )


    def test_camera_timeout_is_preserved(self):

        sample = capture_stability_sample(
            sample_index=0,
            elapsed_seconds=0,
            camera_probe=lambda: "TIMEOUT",
        )

        self.assertEqual(
            sample[
                "camera_status"
            ],
            "TIMEOUT",
        )


    def test_sensor_timeout_is_preserved(self):

        sample = capture_stability_sample(
            sample_index=0,
            elapsed_seconds=0,
            sensor_probe=lambda: "TIMEOUT",
        )

        self.assertEqual(
            sample[
                "sensor_status"
            ],
            "TIMEOUT",
        )


    def test_model_probe_exception_counts_as_crash(self):

        def broken():

            raise RuntimeError(
                "synthetic failure"
            )


        sample = capture_stability_sample(
            sample_index=0,
            elapsed_seconds=0,
            model_probe=broken,
        )

        self.assertEqual(
            sample[
                "model_status"
            ],
            "CRASH",
        )


    def test_summary_tracks_peak_and_growth(self):

        result = summarize_stability_samples(
            [
                fake_sample(
                    0,
                    0,
                    100,
                ),
                fake_sample(
                    1,
                    10,
                    150,
                ),
                fake_sample(
                    2,
                    20,
                    180,
                ),
            ],
            requested_duration_seconds=20,
            runtime_target="TEST",
        )


        self.assertEqual(
            result[
                "peak_rss_bytes"
            ],
            180,
        )

        self.assertEqual(
            result[
                "rss_growth_bytes"
            ],
            80,
        )

        self.assertTrue(
            result[
                "increasing_ram_observed"
            ]
        )

        self.assertFalse(
            result[
                "memory_leak_confirmed"
            ]
        )


    def test_summary_counts_crashes(self):

        result = summarize_stability_samples(
            [
                fake_sample(
                    0,
                    0,
                    100,
                    model="CRASH",
                    api="CRASH",
                ),
                fake_sample(
                    1,
                    10,
                    100,
                ),
            ],
            requested_duration_seconds=10,
            runtime_target="TEST",
        )


        self.assertEqual(
            result[
                "model_crash_count"
            ],
            1,
        )

        self.assertEqual(
            result[
                "api_crash_count"
            ],
            1,
        )


    def test_summary_counts_timeouts(self):

        result = summarize_stability_samples(
            [
                fake_sample(
                    0,
                    0,
                    100,
                    camera="TIMEOUT",
                    sensor="TIMEOUT",
                ),
                fake_sample(
                    1,
                    10,
                    100,
                ),
            ],
            requested_duration_seconds=10,
            runtime_target="TEST",
        )


        self.assertEqual(
            result[
                "camera_timeout_count"
            ],
            1,
        )

        self.assertEqual(
            result[
                "sensor_timeout_count"
            ],
            1,
        )


    def test_db_growth_is_measured(self):

        result = summarize_stability_samples(
            [
                fake_sample(
                    0,
                    0,
                    100,
                    db_size=1000,
                ),
                fake_sample(
                    1,
                    10,
                    100,
                    db_size=1400,
                ),
            ],
            requested_duration_seconds=10,
            runtime_target="TEST",
        )


        self.assertEqual(
            result[
                "db_growth_bytes"
            ],
            400,
        )


    def test_development_target_cannot_pass_final_release_memory_gate(self):

        result = summarize_stability_samples(
            [
                fake_sample(
                    0,
                    0,
                    100,
                ),
                fake_sample(
                    1,
                    1800,
                    100,
                ),
            ],
            requested_duration_seconds=1800,
            runtime_target="DESKTOP_DEVELOPMENT",
            real_hailo_runtime=False,
        )


        self.assertFalse(
            result[
                "final_release_memory_criterion_met"
            ]
        )


    def test_verified_target_can_satisfy_memory_gate_logic(self):

        result = summarize_stability_samples(
            [
                fake_sample(
                    0,
                    0,
                    100,
                ),
                fake_sample(
                    1,
                    1800,
                    100,
                ),
            ],
            requested_duration_seconds=1800,
            runtime_target=FINAL_RUNTIME_TARGET,
            real_hailo_runtime=True,
        )


        self.assertTrue(
            result[
                "final_release_memory_criterion_met"
            ]
        )


    def test_empty_samples_rejected(self):

        with self.assertRaises(
            ValueError
        ):

            summarize_stability_samples(
                [],
                requested_duration_seconds=1800,
                runtime_target="TEST",
            )


    def test_csv_export(self):

        rows = [
            fake_sample(
                0,
                0,
                100,
            )
        ]


        with tempfile.TemporaryDirectory() as tmp:

            output = (
                Path(
                    tmp
                )
                / "stability.csv"
            )

            export_stability_csv(
                rows,
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

                data = list(
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
                data
            ),
            1,
        )


if __name__ == "__main__":
    unittest.main()