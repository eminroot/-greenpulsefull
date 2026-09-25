from __future__ import annotations

from typing import Any


SCHEMA_VERSION = (
    "greenpulse.resource_budget.v1"
)

# Architecture requirement:
# total AI software runtime RAM < 3 GB.
#
# We use decimal GB here:
# 3 GB = 3,000,000,000 bytes.
RAM_LIMIT_BYTES = 3_000_000_000

RAM_LIMIT_GB = 3.0


def evaluate_ram_usage(
    rss_bytes: Any,
) -> dict[str, Any]:

    if (
        isinstance(
            rss_bytes,
            bool,
        )
        or not isinstance(
            rss_bytes,
            int,
        )
        or rss_bytes < 0
    ):

        raise ValueError(
            "rss_bytes must be a non-negative integer."
        )


    within_budget = (
        rss_bytes
        < RAM_LIMIT_BYTES
    )


    return {
        "schema_version":
            SCHEMA_VERSION,

        "rss_bytes":
            rss_bytes,

        "rss_gb_decimal":
            round(
                rss_bytes
                / 1_000_000_000,
                6,
            ),

        "ram_limit_bytes":
            RAM_LIMIT_BYTES,

        "ram_limit_gb_decimal":
            RAM_LIMIT_GB,

        "acceptance_rule":
            "TOTAL_AI_RUNTIME_RAM_STRICTLY_BELOW_3_GB",

        "within_budget":
            within_budget,

        "status":
            (
                "PASS"
                if within_budget
                else "FAIL"
            ),
    }