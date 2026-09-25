import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from src.hailo_deployment_readiness import (
    APPROVAL_SCHEMA_VERSION,
    SCHEMA_VERSION,
    assess_hailo_readiness,
)


def sha256_file(
    path,
):

    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


def make_repo(
    root,
    *,
    approval=False,
    approval_sha_matches=True,
    add_hef=False,
):

    root = Path(
        root
    )

    (
        root
        / "configs"
    ).mkdir(
        parents=True
    )

    (
        root
        / "models"
        / "candidate"
    ).mkdir(
        parents=True
    )


    onnx = (
        root
        / "models"
        / "candidate"
        / "model.onnx"
    )

    onnx.write_bytes(
        b"synthetic-onnx-fixture"
    )


    digest = sha256_file(
        onnx
    )


    registry = {
        "mode":
            "RESEARCH_ONLY",

        "models": {
            "tomato": {
                "onnx": {
                    "path":
                        "models/candidate/model.onnx",

                    "sha256":
                        digest,
                },

                "operational_release_approved":
                    False,
            }
        },
    }


    (
        root
        / "configs"
        / "vision_model_registry_v1.json"
    ).write_text(
        json.dumps(
            registry
        ),
        encoding="utf-8",
    )


    if approval:

        approval_digest = (
            digest
            if approval_sha_matches
            else "0" * 64
        )


        payload = {
            "schema_version":
                APPROVAL_SCHEMA_VERSION,

            "approved_by_role":
                "ENGINEER_1",

            "approval_status":
                "APPROVED_FOR_HAILO_CONVERSION",

            "approved_onnx": {
                "path":
                    "models/candidate/model.onnx",

                "sha256":
                    approval_digest,
            },
        }


        (
            root
            / "configs"
            / "hailo_edge_approval_v1.json"
        ).write_text(
            json.dumps(
                payload
            ),
            encoding="utf-8",
        )


    if add_hef:

        (
            root
            / "models"
            / "candidate"
            / "model.hef"
        ).write_bytes(
            b"synthetic-hef-placeholder"
        )


class TestHailoDeploymentReadiness(
    unittest.TestCase
):

    def test_schema_version(self):

        self.assertEqual(
            SCHEMA_VERSION,
            "greenpulse.hailo_deployment_readiness.v1",
        )


    def test_missing_engineer1_approval_blocks_conversion(self):

        with tempfile.TemporaryDirectory() as tmp:

            make_repo(
                tmp
            )

            result = assess_hailo_readiness(
                Path(
                    tmp
                ),

                toolchain_override={
                    "conversion_toolchain_detected":
                        True,

                    "runtime_detected":
                        True,
                },
            )


        self.assertFalse(
            result[
                "ready_for_conversion"
            ]
        )

        self.assertIn(
            "ENGINEER1_HAILO_APPROVAL_EVIDENCE_MISSING",
            result[
                "blockers"
            ],
        )


    def test_hash_mismatch_blocks_approval(self):

        with tempfile.TemporaryDirectory() as tmp:

            make_repo(
                tmp,
                approval=True,
                approval_sha_matches=False,
            )

            result = assess_hailo_readiness(
                Path(
                    tmp
                ),

                toolchain_override={
                    "conversion_toolchain_detected":
                        True,

                    "runtime_detected":
                        True,
                },
            )


        self.assertFalse(
            result[
                "ready_for_conversion"
            ]
        )


    def test_verified_approval_and_toolchain_is_ready(self):

        with tempfile.TemporaryDirectory() as tmp:

            make_repo(
                tmp,
                approval=True,
            )

            result = assess_hailo_readiness(
                Path(
                    tmp
                ),

                toolchain_override={
                    "conversion_toolchain_detected":
                        True,

                    "runtime_detected":
                        True,
                },
            )


        self.assertTrue(
            result[
                "ready_for_conversion"
            ]
        )

        self.assertEqual(
            result[
                "status"
            ],
            "READY_FOR_HAILO_CONVERSION",
        )


    def test_missing_toolchain_blocks_conversion(self):

        with tempfile.TemporaryDirectory() as tmp:

            make_repo(
                tmp,
                approval=True,
            )

            result = assess_hailo_readiness(
                Path(
                    tmp
                ),

                toolchain_override={
                    "conversion_toolchain_detected":
                        False,

                    "runtime_detected":
                        False,
                },
            )


        self.assertFalse(
            result[
                "ready_for_conversion"
            ]
        )


    def test_hef_presence_does_not_complete_layer(self):

        with tempfile.TemporaryDirectory() as tmp:

            make_repo(
                tmp,
                approval=True,
                add_hef=True,
            )

            result = assess_hailo_readiness(
                Path(
                    tmp
                ),

                toolchain_override={
                    "conversion_toolchain_detected":
                        True,

                    "runtime_detected":
                        True,
                },
            )


        self.assertFalse(
            result[
                "layer41_complete"
            ]
        )

        self.assertFalse(
            result[
                "hailo_onnx_regression_verified"
            ]
        )

        self.assertFalse(
            result[
                "raspberry_pi_5_inference_verified"
            ]
        )


    def test_registry_operational_false_not_rewritten_as_edge_approval(self):

        with tempfile.TemporaryDirectory() as tmp:

            make_repo(
                tmp
            )

            result = assess_hailo_readiness(
                Path(
                    tmp
                ),

                toolchain_override={
                    "conversion_toolchain_detected":
                        True,

                    "runtime_detected":
                        True,
                },
            )


        candidate = result[
            "candidate_models"
        ][0]


        self.assertFalse(
            candidate[
                "operational_release_approved"
            ]
        )

        self.assertIsNone(
            result[
                "approved_candidate"
            ]
        )


    def test_desktop_readiness_never_claims_pi_validation(self):

        with tempfile.TemporaryDirectory() as tmp:

            make_repo(
                tmp,
                approval=True,
            )

            result = assess_hailo_readiness(
                Path(
                    tmp
                ),

                toolchain_override={
                    "conversion_toolchain_detected":
                        True,

                    "runtime_detected":
                        True,
                },
            )


        self.assertFalse(
            result[
                "raspberry_pi_5_inference_verified"
            ]
        )

        self.assertFalse(
            result[
                "ai_hat_plus_inference_verified"
            ]
        )


if __name__ == "__main__":
    unittest.main()