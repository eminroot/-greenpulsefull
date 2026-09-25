
def evaluate_safety(observation):
    """Conservative irrigation safety assessment."""

    reasons = ["WATER_STRESS_MODEL_NOT_VALIDATED"]

    # Physical controller is not connected or verified.
    reasons.append("HARDWARE_NOT_CONNECTED")

    sensor = observation.get("sensor") or {}
    sensor_status = sensor.get("status")

    if sensor_status == "MISSING":
        reasons.append("SENSOR_MISSING")
    elif sensor_status == "VALID_SIMULATED":
        reasons.append("SENSOR_SIMULATED")
    elif sensor_status == "VALID":
        # A client's REAL declaration is not device authentication.
        reasons.append("SENSOR_IDENTITY_NOT_VERIFIED")
    else:
        reasons.append("SENSOR_NOT_VALIDATED")

    image = observation.get("image_capture") or {}

    if image.get("verified") is not True:
        reasons.append("IMAGE_CAPTURE_TIME_NOT_VERIFIED")

    sync = observation.get("time_sync") or {}

    if sync.get("status") != "SYNCED":
        reasons.append("IMAGE_SENSOR_NOT_SYNCHRONIZED")

    # Never infer water stress from disease classification.
    # No physical action is permitted at this development stage.
    return {
        "action": "NO_AUTONOMOUS_ACTION",
        "reason_codes": reasons,
        "safety_gate_version": "1.0"
    }
