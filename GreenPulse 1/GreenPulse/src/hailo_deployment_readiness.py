from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

import hashlib
import importlib.util
import json
import shutil


SCHEMA_VERSION = (
    "greenpulse.hailo_deployment_readiness.v1"
)

APPROVAL_SCHEMA_VERSION = (
    "greenpulse.hailo_edge_approval.v1"
)


def sha256_file(
    path: Path,
) -> str:

    h = hashlib.sha256()

    with path.open(
        "rb"
    ) as stream:

        for block in iter(
            lambda: stream.read(
                1024 * 1024
            ),
            b"",
        ):

            h.update(
                block
            )

    return h.hexdigest()


def _extract_models(
    registry: Mapping[
        str,
        Any,
    ],
) -> dict[str, Mapping[str, Any]]:

    models = registry.get(
        "models"
    )

    if isinstance(
        models,
        Mapping,
    ):

        return {
            str(
                key
            ):
                value

            for key, value
            in models.items()

            if isinstance(
                value,
                Mapping,
            )
        }


    result = {}


    for key, value in registry.items():

        if (
            isinstance(
                value,
                Mapping,
            )
            and isinstance(
                value.get(
                    "onnx"
                ),
                Mapping,
            )
        ):

            result[
                str(
                    key
                )
            ] = value


    return result


def detect_hailo_toolchain() -> dict[str, Any]:

    packages = {}


    for name in (
        "hailo_platform",
        "hailo_sdk_client",
    ):

        packages[
            name
        ] = (
            importlib.util.find_spec(
                name
            )
            is not None
        )


    executables = {}


    for name in (
        "hailortcli",
        "hailo",
        "hailo-parse-hef",
    ):

        executables[
            name
        ] = shutil.which(
            name
        )


    conversion_detected = (
        packages[
            "hailo_sdk_client"
        ]
        or executables[
            "hailo"
        ]
        is not None
    )


    runtime_detected = (
        packages[
            "hailo_platform"
        ]
        or executables[
            "hailortcli"
        ]
        is not None
    )


    return {
        "packages":
            packages,

        "executables":
            executables,

        "conversion_toolchain_detected":
            conversion_detected,

        "runtime_detected":
            runtime_detected,
    }


def assess_hailo_readiness(
    root: Path,
    *,
    toolchain_override: Optional[
        Mapping[str, Any]
    ] = None,
) -> dict[str, Any]:

    root = Path(
        root
    ).resolve()


    registry_path = (
        root
        / "configs"
        / "vision_model_registry_v1.json"
    )

    approval_path = (
        root
        / "configs"
        / "hailo_edge_approval_v1.json"
    )


    blockers = []


    if not registry_path.is_file():

        return {
            "schema_version":
                SCHEMA_VERSION,

            "status":
                "BLOCKED",

            "blockers": [
                "VISION_MODEL_REGISTRY_MISSING"
            ],

            "ready_for_conversion":
                False,

            "layer41_complete":
                False,
        }


    registry = json.loads(
        registry_path.read_text(
            encoding="utf-8-sig"
        )
    )


    models = _extract_models(
        registry
    )


    candidates = []


    for crop, model in models.items():

        onnx = model.get(
            "onnx"
        )


        if not isinstance(
            onnx,
            Mapping,
        ):

            continue


        relative_path = onnx.get(
            "path"
        )

        expected_sha = onnx.get(
            "sha256"
        )


        artifact_exists = False
        hash_verified = False
        actual_sha = None


        if (
            isinstance(
                relative_path,
                str,
            )
            and relative_path.strip()
        ):

            artifact_path = (
                root
                / relative_path
            )


            if artifact_path.is_file():

                artifact_exists = True

                actual_sha = sha256_file(
                    artifact_path
                )


                if (
                    isinstance(
                        expected_sha,
                        str,
                    )
                    and actual_sha
                    == expected_sha
                ):

                    hash_verified = True


        candidates.append(
            {
                "crop":
                    crop,

                "onnx_path":
                    relative_path,

                "expected_sha256":
                    expected_sha,

                "actual_sha256":
                    actual_sha,

                "artifact_exists":
                    artifact_exists,

                "hash_verified":
                    hash_verified,

                "operational_release_approved":
                    (
                        model.get(
                            "operational_release_approved"
                        )
                        is True
                    ),
            }
        )


    approval = None
    approved_candidate = None


    if not approval_path.is_file():

        blockers.append(
            "ENGINEER1_HAILO_APPROVAL_EVIDENCE_MISSING"
        )

    else:

        approval = json.loads(
            approval_path.read_text(
                encoding="utf-8-sig"
            )
        )


        if (
            approval.get(
                "schema_version"
            )
            != APPROVAL_SCHEMA_VERSION
        ):

            blockers.append(
                "INVALID_HAILO_APPROVAL_SCHEMA"
            )

        elif (
            approval.get(
                "approved_by_role"
            )
            != "ENGINEER_1"
        ):

            blockers.append(
                "APPROVAL_ROLE_IS_NOT_ENGINEER_1"
            )

        elif (
            approval.get(
                "approval_status"
            )
            != "APPROVED_FOR_HAILO_CONVERSION"
        ):

            blockers.append(
                "HAILO_CONVERSION_NOT_APPROVED"
            )

        else:

            approved_onnx = approval.get(
                "approved_onnx"
            )


            if not isinstance(
                approved_onnx,
                Mapping,
            ):

                blockers.append(
                    "APPROVED_ONNX_DESCRIPTOR_MISSING"
                )

            else:

                approved_path = (
                    approved_onnx.get(
                        "path"
                    )
                )

                approved_sha = (
                    approved_onnx.get(
                        "sha256"
                    )
                )


                matches = [
                    candidate

                    for candidate
                    in candidates

                    if (
                        candidate[
                            "onnx_path"
                        ]
                        == approved_path

                        and candidate[
                            "expected_sha256"
                        ]
                        == approved_sha

                        and candidate[
                            "hash_verified"
                        ]
                        is True
                    )
                ]


                if len(
                    matches
                ) != 1:

                    blockers.append(
                        "APPROVED_ONNX_NOT_VERIFIED_IN_REGISTRY"
                    )

                else:

                    approved_candidate = (
                        matches[0]
                    )


    toolchain = (
        dict(
            toolchain_override
        )
        if toolchain_override
        is not None
        else detect_hailo_toolchain()
    )


    if (
        toolchain.get(
            "conversion_toolchain_detected"
        )
        is not True
    ):

        blockers.append(
            "HAILO_CONVERSION_TOOLCHAIN_NOT_AVAILABLE"
        )


    hef_files = []


    models_dir = (
        root
        / "models"
    )


    if models_dir.exists():

        for path in models_dir.rglob(
            "*.hef"
        ):

            if path.is_file():

                hef_files.append(
                    str(
                        path.relative_to(
                            root
                        )
                    ).replace(
                        "\\",
                        "/",
                    )
                )


    ready_for_conversion = (
        approved_candidate
        is not None

        and toolchain.get(
            "conversion_toolchain_detected"
        )
        is True
    )


    if ready_for_conversion:

        if hef_files:

            status = (
                "HEF_PRESENT_REGRESSION_AND_EDGE_VALIDATION_PENDING"
            )

        else:

            status = (
                "READY_FOR_HAILO_CONVERSION"
            )

    else:

        status = (
            "BLOCKED_PRE_DEPLOYMENT_REQUIREMENTS"
        )


    return {
        "schema_version":
            SCHEMA_VERSION,

        "status":
            status,

        "registry_path":
            "configs/vision_model_registry_v1.json",

        "approval_path":
            "configs/hailo_edge_approval_v1.json",

        "approval_evidence_present":
            approval
            is not None,

        "approved_candidate":
            approved_candidate,

        "candidate_models":
            candidates,

        "toolchain":
            toolchain,

        "hef_files":
            hef_files,

        "ready_for_conversion":
            ready_for_conversion,

        "onnx_to_hef_conversion_verified":
            False,

        "hailo_onnx_regression_verified":
            False,

        "raspberry_pi_5_inference_verified":
            False,

        "ai_hat_plus_inference_verified":
            False,

        "training_stack_absent_from_edge_verified":
            False,

        "layer41_complete":
            False,

        "blockers":
            list(
                dict.fromkeys(
                    blockers
                )
            ),

        "scientific_guardrails": {
            "registry_candidate_equals_engineer1_approval":
                False,

            "onnx_presence_equals_hef_conversion":
                False,

            "hef_presence_equals_regression_pass":
                False,

            "desktop_test_equals_pi_hailo_validation":
                False,

            "classification_model_claimed_as_water_stress_model":
                False,
        },
    }