import json
import tempfile
from time import perf_counter

from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
from io import BytesIO

from PIL import Image
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query

from src.sensor_validator import validate_sensor
from src.sensor_contract_guard import check_sensor_contract
from src.time_sync import synchronize

from src.ai_gateway_service import (
    run_diagnostic_vision,
    get_model_registry_info,
    get_recent_event_view,
    get_recent_sensor_view,
    get_recent_hardware_action_view,
    get_hardware_action_view,
)

from src.ai_output_contract import (
    build_standard_ai_output,
)
from src.audit_db import log_observation, get_latest_observation, get_plant_history
from src.safety_gate import evaluate_safety
from src.sensor_features import extract_sensor_features
from src.sensor_history import select_previous_sensor
from src.sensor_window import calculate_sensor_window
from src.fusion_contract import prepare_fusion_inputs
from src.image_quality import check_image_quality
from src.hardware_contract import prepare_hardware_handoff
from src.observation_freshness import check_observation_freshness


app = FastAPI(
    title="GreenPulse AI API",
    version="0.1.0",
    description="GreenPulse Vision and Sensor Integration"
)


@app.get("/status")
def status():
    return {
        "system": "GreenPulse",
        "status": "RUNNING",
        "vision_model": "YOLO11n Classification",
        "supported_crops": ["tomato"],
        "hardware": "NOT_CONNECTED",
        "autonomous_irrigation": False
    }


@app.post("/inference")
async def inference(
    image: UploadFile = File(...),
    plant_id: str = Form(...),
    crop: str = Form("tomato"),
    sensor_json: str | None = Form(None),
    image_captured_at: str | None = Form(None)
):

    inference_started = perf_counter()

    if crop != "tomato":
        raise HTTPException(
            status_code=422,
            detail="This model currently supports tomato only."
        )

    if not plant_id.strip():
        raise HTTPException(
            status_code=422,
            detail="Plant ID is required."
        )

    content = await image.read(8 * 1024 * 1024 + 1)
    await image.close()

    if len(content) > 8 * 1024 * 1024:
        raise HTTPException(
            status_code=413,
            detail="Image exceeds 8 MB."
        )

    try:
        with Image.open(BytesIO(content)) as img:
            if img.format not in ("JPEG", "PNG"):
                raise ValueError("Unsupported image format")

            if min(img.size) < 96:
                raise ValueError("Image resolution too low")

            image_format = img.format
            img.verify()

    except Exception:
        raise HTTPException(
            status_code=422,
            detail="Invalid or unsupported image."
        )

    sensor_status = "MISSING"
    sensor_reason = "sensor_packet_not_provided"
    sensor_data = None

    if sensor_json is not None:
        try:
            sensor_data = json.loads(sensor_json)

            if not isinstance(sensor_data, dict):
                raise ValueError()

        except (ValueError, TypeError):
            raise HTTPException(
                status_code=422,
                detail="Invalid sensor JSON."
            )

        contract_valid, contract_errors = check_sensor_contract(
            sensor_data
        )

        if not contract_valid:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "Sensor schema validation failed.",
                    "issues": contract_errors
                }
            )

        sensor_status, sensor_reason = validate_sensor(
            sensor_data
        )

        if sensor_data.get("plant_id") != plant_id:
            raise HTTPException(
                status_code=422,
                detail="Sensor and image plant IDs differ."
            )


    if sensor_data is None:
        sync_result = {
            "status": "NO_SENSOR_DATA",
            "delta_seconds": None
        }
    elif sensor_status not in ("VALID", "VALID_SIMULATED"):
        sync_result = {
            "status": "SENSOR_NOT_VALID",
            "delta_seconds": None
        }
    else:
        sync_result = synchronize(
            image_captured_at,
            sensor_data["timestamp"]
        )

    # Reject unusable images before running the AI model.
    quality = check_image_quality(content)

    if not quality["eligible_for_inference"]:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "IMAGE_QUALITY_REJECTED",
                "quality": quality,
                "next_step": "RECAPTURE_REQUEST"
            }
        )

    suffix = ".jpg" if image_format == "JPEG" else ".png"

    with tempfile.TemporaryDirectory() as temp_dir:
        image_path = Path(temp_dir) / ("input" + suffix)
        image_path.write_bytes(content)

        result = run_diagnostic_vision(
            image_path=image_path,
            crop=crop,
        )

    observation_id = str(uuid4())

    response = {
        "schema_version": "0.6.0",
        "observation_id": observation_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "plant_id": plant_id,
        "crop": crop,
        "image_capture": {
            "timestamp": image_captured_at,
            "source": (
                "CLIENT_DECLARED" if image_captured_at
                else "UNKNOWN"
            ),
            "verified": False
        },
        "time_sync": sync_result,
        "vision": result["vision"],
        "sensor": {
            "status": sensor_status,
            "reason": sensor_reason,
            "data": sensor_data
        },
        "water_stress_risk": None,
        "forecast": None,
        "decision": {
            "action": "NO_AUTONOMOUS_ACTION",
            "reason_codes": [
                "WATER_STRESS_MODEL_NOT_VALIDATED"
            ]
        },
        "model": result["model"]
    }

    # Extract features only from validated sensor data.
    # Simulated or unauthenticated data remains explicitly marked.
    response["sensor_features"] = None
    response["sensor_window"] = None

    if (
        sensor_data is not None
        and sensor_status in ("VALID", "VALID_SIMULATED")
    ):
        try:
            # Read previous observations for the same plant.
            # Only eligible sensor packets can be compared.
            history = get_plant_history(
                plant_id,
                limit=100
            )

            previous_packet = select_previous_sensor(
                sensor_data,
                history
            )

            response["sensor_features"] = (
                extract_sensor_features(
                    sensor_data,
                    previous_packet
                )
            )

            response["sensor_window"] = (
                calculate_sensor_window(
                    sensor_data,
                    history,
                    window_minutes=30
                )
            )
        except ValueError:
            # Feature extraction failure must never
            # produce an irrigation request.
            response["sensor_features"] = None

    # Prepare diagnostic multimodal inputs.
    # This is NOT a trained fusion model.
    # Include image quality in the recorded observation.
    response["image_quality"] = quality

    response["fusion_inputs"] = (
        prepare_fusion_inputs(response)
    )

    response['decision'] = evaluate_safety(response)

    # Prepare a blocked hardware handoff.
    # No real actuator command is generated.
    response["hardware_handoff"] = (
        prepare_hardware_handoff(response)
    )

    try:
        log_observation(response, content)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Audit logging unavailable."
        )

    latency_ms = (
        perf_counter()
        - inference_started
    ) * 1000.0

    return build_standard_ai_output(
        response,
        latency_ms=latency_ms,
    )



@app.get("/latest")
def latest():

    try:
        result = get_latest_observation()

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Observation database unavailable."
        )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="No observations available."
        )

    # Calculate freshness when the result is requested.
    # The original database record remains unchanged.
    response = result.copy()

    response["observation_freshness"] = (
        check_observation_freshness(
            result.get("timestamp")
        )
    )

    standard = build_standard_ai_output(
        response
    )

    standard[
        "observation_freshness"
    ] = response.get(
        "observation_freshness"
    )

    return standard



@app.get("/plants/{plant_id}")
def plant_history(
    plant_id: str,
    limit: int = Query(default=10, ge=1, le=100)
):

    if not plant_id.strip() or len(plant_id) > 64:
        raise HTTPException(
            status_code=422,
            detail="Invalid plant ID."
        )

    try:
        observations = get_plant_history(
            plant_id,
            limit
        )

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Observation database unavailable."
        )

    # Calculate freshness separately for each observation.
    # Do not modify the original database records.
    annotated_observations = [
        {
            **observation,
            "observation_freshness": (
                check_observation_freshness(
                    observation.get("timestamp")
                )
            )
        }
        for observation in observations
    ]

    standardized_observations = []

    for observation in annotated_observations:

        standard = build_standard_ai_output(
            observation
        )

        standard[
            "observation_freshness"
        ] = observation.get(
            "observation_freshness"
        )

        standardized_observations.append(
            standard
        )

    return {
        "schema_version":
            "greenpulse.standard_ai_output_collection.v1",

        "plant_id":
            plant_id,

        "count":
            len(
                standardized_observations
            ),

        "observations":
            standardized_observations,
    }


# Development-only endpoint.
# Never exposes a physical actuator control operation.
from fastapi import Request
from src.actuator_query import get_recent_simulated_events



@app.get("/events")
def events(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    )
):
    """
    Read-only AI observation event view.

    Source:
    persisted observation audit log.

    This endpoint does not dispatch hardware.
    """

    try:
        return get_recent_event_view(
            limit=limit,
        )

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Observation event view unavailable.",
        )


@app.get("/model/info")
def model_info():
    """
    Read research-only model registry metadata.

    Does not instantiate or execute a model.
    Does not expose local artifact paths.
    """

    try:
        return get_model_registry_info()

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Model registry unavailable.",
        )


@app.get("/sensors")
def sensors(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    plant_id: str | None = Query(
        default=None,
        max_length=64,
    ),
):
    """
    Read-only sensor snapshots extracted from
    persisted observation audit records.

    Sensor source fields are not authentication.
    """

    try:
        return get_recent_sensor_view(
            limit=limit,
            plant_id=plant_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="Sensor observation view unavailable.",
        )



@app.get("/actions")
def hardware_actions(
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    )
):
    """
    Read-only canonical hardware action-state view.

    This endpoint does not dispatch commands and does
    not claim that simulated or unverified ACK records
    are real hardware execution evidence.
    """

    try:

        return get_recent_hardware_action_view(
            limit=limit,
        )

    except Exception:

        raise HTTPException(
            status_code=503,
            detail="Hardware action-state audit unavailable.",
        )


@app.get("/actions/{command_id}")
def hardware_action(
    command_id: str,
):
    """
    Read one canonical action state by command_id.

    No hardware communication occurs here.
    """

    try:

        result = get_hardware_action_view(
            command_id
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        )

    except Exception:

        raise HTTPException(
            status_code=503,
            detail="Hardware action-state audit unavailable.",
        )


    if result is None:

        raise HTTPException(
            status_code=404,
            detail="Hardware action state not found.",
        )


    return result


@app.get("/simulated-actuator/events")
def read_simulated_actuator_events(
    request: Request,
    limit: int = 20
):
    import os

    # Explicit opt-in required.
    if (
        os.environ.get(
            "GREENPULSE_ENABLE_SIMULATION_API"
        ) != "1"
    ):
        raise HTTPException(
            status_code=404,
            detail="Not found"
        )

    # This is not a production authentication system.
    if (
        request.client is None
        or request.client.host
        not in ("127.0.0.1", "::1")
    ):
        raise HTTPException(
            status_code=403,
            detail="Local development access only"
        )

    if not 1 <= limit <= 100:
        raise HTTPException(
            status_code=422,
            detail="Limit must be between 1 and 100"
        )

    try:
        events = get_recent_simulated_events(limit)

    except Exception:
        raise HTTPException(
            status_code=503,
            detail="SIMULATION_AUDIT_UNAVAILABLE"
        )

    return {
        "schema_version": "0.1.0",
        "data_origin": "SIMULATED_TEST_HARNESS",
        "physical_actuation": False,
        "real_hardware_ack_available": False,
        "count": len(events),
        "events": events
    }


# ======================================
# DEVELOPMENT-ONLY CLOSED-LOOP FEEDBACK
# ======================================

import os
import sqlite3

from uuid import UUID

from src.closed_loop_feedback_contract import (
    get_simulated_feedback
)


@app.get(
    "/simulated-actuator/feedback/{command_id}"
)
def read_simulated_closed_loop_feedback(
    request: Request,
    command_id: str
):
    """
    Read recorded synthetic feedback only.

    No real hardware access.
    No physical actuator control.
    """

    if os.environ.get(
        "GREENPULSE_ENABLE_SIMULATION_API"
    ) != "1":
        raise HTTPException(
            status_code=404,
            detail="Not found"
        )

    if (
        request.client is None
        or request.client.host
        not in ("127.0.0.1", "::1")
    ):
        raise HTTPException(
            status_code=403,
            detail="Local development access only"
        )

    try:
        validated_id = str(
            UUID(command_id)
        )

    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=422,
            detail="INVALID_COMMAND_ID"
        )

    try:
        feedback = get_simulated_feedback(
            validated_id
        )

    except (
        FileNotFoundError,
        sqlite3.DatabaseError,
        ValueError
    ):
        raise HTTPException(
            status_code=503,
            detail="SIMULATED_FEEDBACK_UNAVAILABLE"
        )

    if feedback is None:
        raise HTTPException(
            status_code=404,
            detail="SIMULATED_FEEDBACK_NOT_FOUND"
        )

    return feedback
