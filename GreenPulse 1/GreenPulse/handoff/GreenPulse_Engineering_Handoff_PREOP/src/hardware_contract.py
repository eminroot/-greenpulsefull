
HARDWARE_CONTRACT_VERSION = "0.1.0"


def prepare_hardware_handoff(observation):
    """
    Prepare a safe hardware handoff.

    Real command dispatch is disabled until the
    hardware, risk model and safety policy are validated.
    """

    if not isinstance(observation, dict):
        raise ValueError("Observation must be a dictionary.")

    decision = observation.get("decision") or {}

    if not isinstance(decision, dict):
        raise ValueError("Invalid decision structure.")

    existing_reasons = decision.get("reason_codes") or []

    if not isinstance(existing_reasons, list):
        raise ValueError("Invalid reason codes.")

    reasons = [
        "HARDWARE_NOT_CONNECTED",
        "WATER_STRESS_MODEL_NOT_VALIDATED",
        "REAL_ACTUATION_DISABLED"
    ]

    for reason in existing_reasons:
        if isinstance(reason, str) and reason not in reasons:
            reasons.append(reason)

    if decision.get("action") != "NO_AUTONOMOUS_ACTION":
        reasons.append("UNSUPPORTED_DECISION_BLOCKED")

    return {
        "contract_version": HARDWARE_CONTRACT_VERSION,
        "observation_id": observation.get("observation_id"),
        "plant_id": observation.get("plant_id"),
        "mode": "SIMULATION_ONLY",
        "status": "BLOCKED",
        "dispatch_permitted": False,
        "actuator_request": None,
        "hardware_ack": None,
        "reason_codes": reasons
    }
