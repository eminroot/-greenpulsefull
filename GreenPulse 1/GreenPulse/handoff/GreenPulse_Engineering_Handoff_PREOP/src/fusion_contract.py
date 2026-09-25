
FUSION_SCHEMA_VERSION = "0.1.0"


def prepare_fusion_inputs(observation):
    """
    Prepare diagnostic multimodal inputs.

    This function DOES NOT estimate water stress.
    It DOES NOT authorize irrigation.
    """

    sensor = observation.get("sensor") or {}
    features = observation.get("sensor_features") or {}
    window = observation.get("sensor_window") or {}
    vision = observation.get("vision") or {}
    image = observation.get("image_capture") or {}
    sync = observation.get("time_sync") or {}

    reasons = [
        "FUSION_MODEL_NOT_TRAINED",
        "WATER_STRESS_LABELS_NOT_VALIDATED"
    ]

    if sensor.get("status") != "VALID":
        reasons.append("REAL_SENSOR_DATA_NOT_VERIFIED")

    provenance = features.get("provenance") or {}

    if provenance.get("device_authenticated") is not True:
        reasons.append("SENSOR_DEVICE_NOT_AUTHENTICATED")

    if image.get("verified") is not True:
        reasons.append("IMAGE_CAPTURE_NOT_VERIFIED")

    if sync.get("status") != "SYNCED":
        reasons.append("IMAGE_SENSOR_NOT_SYNCHRONIZED")

    current = features.get("current") or {}
    trend = features.get("trend") or {}
    averages = window.get("averages") or {}

    return {
        "schema_version": FUSION_SCHEMA_VERSION,
        "status": "NOT_READY",
        "eligible_for_operational_risk": False,

        "diagnostic_sensor_inputs": {
            "soil_moisture_pct": current.get(
                "soil_moisture_pct"
            ),
            "temperature_c": current.get(
                "temperature_c"
            ),
            "humidity_pct": current.get(
                "humidity_pct"
            ),
            "soil_moisture_change_per_hour": trend.get(
                "soil_moisture_change_per_hour"
            ),
            "rolling_soil_moisture_pct": averages.get(
                "soil_moisture_pct"
            )
        },

        # Disease classification is contextual information.
        # It must NOT be interpreted as water-stress risk.
        "visual_context": {
            "disease_class": vision.get(
                "predicted_class"
            ),
            "classification_confidence": vision.get(
                "confidence"
            ),
            "confidence_calibrated": vision.get(
                "confidence_calibrated", False
            )
        },

        "sensor_provenance": provenance,
        "blocking_reasons": reasons,
        "water_stress_probability": None,
        "water_stress_risk": None,
        "irrigation_authorized": False
    }
