import os
import unittest

from src.resource_budget import (
    RAM_LIMIT_BYTES,
    SCHEMA_VERSION,
    evaluate_ram_usage,
)

from src.resource_monitor import (
    MONITOR_SCHEMA_VERSION,
    process_tree_rss_bytes,
    summarize_memory_samples,
)


class TestResourceBudget(
    unittest.TestCase
):

    def test_schema_version(self):

        self.assertEqual(
            SCHEMA_VERSION,
            "greenpulse.resource_budget.v1",
        )


    def test_limit_is_three_decimal_gb(self):

        self.assertEqual(
            RAM_LIMIT_BYTES,
            3_000_000_000,
        )


    def test_below_limit_passes(self):

        result = evaluate_ram_usage(
            2_999_999_999
        )

        self.assertTrue(
            result[
                "within_budget"
            ]
        )

        self.assertEqual(
            result[
                "status"
            ],
            "PASS",
        )


    def test_exact_limit_fails(self):

        result = evaluate_ram_usage(
            3_000_000_000
        )

        self.assertFalse(
            result[
                "within_budget"
            ]
        )

        self.assertEqual(
            result[
                "status"
            ],
            "FAIL",
        )


    def test_above_limit_fails(self):

        result = evaluate_ram_usage(
            3_100_000_000
        )

        self.assertFalse(
            result[
                "within_budget"
            ]
        )


    def test_invalid_ram_input_rejected(self):

        with self.assertRaises(
            ValueError
        ):

            evaluate_ram_usage(
                -1
            )


    def test_monitor_schema_version(self):

        self.assertEqual(
            MONITOR_SCHEMA_VERSION,
            "greenpulse.runtime_memory_monitor.v1",
        )


    def test_sample_summary_uses_peak(self):

        result = summarize_memory_samples(
            [
                1_000_000_000,
                2_500_000_000,
                2_000_000_000,
            ]
        )

        self.assertEqual(
            result[
                "peak_rss_bytes"
            ],
            2_500_000_000,
        )

        self.assertTrue(
            result[
                "within_budget"
            ]
        )


    def test_summary_fails_when_peak_hits_limit(self):

        result = summarize_memory_samples(
            [
                1_000_000_000,
                3_000_000_000,
            ]
        )

        self.assertFalse(
            result[
                "within_budget"
            ]
        )


    def test_current_process_tree_measurement(self):

        result = process_tree_rss_bytes(
            os.getpid()
        )

        self.assertGreater(
            result[
                "rss_bytes"
            ],
            0,
        )

        self.assertIn(
            os.getpid(),
            result[
                "measured_pids"
            ],
        )


    def test_empty_samples_rejected(self):

        with self.assertRaises(
            ValueError
        ):

            summarize_memory_samples(
                []
            )


if __name__ == "__main__":
    unittest.main()