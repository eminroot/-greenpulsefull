
import json
import math

from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

POLICY = json.loads(
    (
        ROOT
        / "configs"
        / "simulated_irrigation_policy_v1.json"
    ).read_text(encoding="utf-8")
)


def evaluate_simulated_irrigation(payload):
    """
    Deterministic development-only irrigation policy.

    Synthetic thresholds have no operational validity.
    This function never creates a physical pump command.
    """

    result = {
        "policy_version": POLICY["policy_version"],
        "mode": "SIMULATION_ONLY",
        "decision": "SIMULATED_RECHECK",
        "eligible_for_simulated_pump": False,
        "physical_actuation": False,
        "operational_irrigation_authorized": False,
        "water_stress_risk": None,
        "reason_codes": []
    }

    def reject(reason):
        result["reason_codes"].append(reason)
        return result

    if not isinstance(payload, dict):
        return reject("INVALID_TEST_INPUT")

    if (
        payload.get("mode") != "SIMULATION_ONLY"
        or payload.get("origin") != "TEST_HARNESS"
        or payload.get("test_only") is not True
    ):
        return reject("TEST_MODE_REQUIRED")

    samples = payload.get("sensor_samples")

    if not isinstance(samples, list):
        return reject("INVALID_SENSOR_HISTORY")

    minimum = POLICY["minimum_consecutive_samples"]

    if len(samples) < minimum:
        return reject("INSUFFICIENT_SENSOR_HISTORY")

    try:
        reference = datetime.fromisoformat(
            payload["reference_at"]
        )

        if reference.tzinfo is None:
            raise ValueError("Timezone required.")

        parsed = []

        for sample in samples:
            if not isinstance(sample, dict):
                raise ValueError("Invalid sample.")

            if sample.get("source") != "SIMULATED":
                raise ValueError("Unverified sample source.")

            value = sample["soil_moisture_pct"]

            if (
                type(value) not in (int, float)
                or not math.isfinite(value)
                or not 0 <= value <= 100
            ):
                raise ValueError("Invalid moisture.")

            timestamp = datetime.fromisoformat(
                sample["timestamp"]
            )

            if timestamp.tzinfo is None:
                raise ValueError("Timezone required.")

            parsed.append((timestamp, value))

    except (
        KeyError,
        TypeError,
        ValueError
    ):
        return reject("INVALID_SIMULATED_SENSOR_PACKET")

    timestamps = [item[0] for item in parsed]

    if any(
        current <= previous
        for previous, current in zip(
            timestamps,
            timestamps[1:]
        )
    ):
        return reject("NON_CHRONOLOGICAL_HISTORY")

    latest_age = (
        reference - timestamps[-1]
    ).total_seconds()

    window_seconds = (
        timestamps[-1] - timestamps[0]
    ).total_seconds()

    if (
        latest_age < 0
        or latest_age
        > POLICY["max_latest_sample_age_seconds"]
        or window_seconds
        > POLICY["max_sample_window_seconds"]
    ):
        return reject("STALE_OR_INVALID_TEST_WINDOW")

    recent = parsed[-minimum:]

    threshold = POLICY[
        "synthetic_low_moisture_below_pct"
    ]

    if not all(
        moisture < threshold
        for _, moisture in recent
    ):
        result["decision"] = "SIMULATED_MONITOR"

        return reject(
            "LOW_MOISTURE_NOT_CONSECUTIVELY_CONFIRMED"
        )

    cooldown = payload.get(
        "seconds_since_last_simulated_action"
    )

    if cooldown is not None:
        if (
            type(cooldown) not in (int, float)
            or not math.isfinite(cooldown)
            or cooldown < 0
        ):
            return reject("INVALID_TEST_COOLDOWN")

        if cooldown < POLICY[
            "minimum_simulated_cooldown_seconds"
        ]:
            result["decision"] = "SIMULATED_MONITOR"

            return reject(
                "SIMULATED_COOLDOWN_ACTIVE"
            )

    result["decision"] = (
        "SIMULATED_IRRIGATION_ELIGIBLE"
    )

    result["eligible_for_simulated_pump"] = True

    result["reason_codes"] = [
        "SYNTHETIC_LOW_MOISTURE_CONFIRMED",
        "SIMULATED_SAFETY_CHECKS_PASSED"
    ]

    return result
