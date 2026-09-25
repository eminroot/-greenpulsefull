import json
import tempfile
import unittest
from pathlib import Path

from src.version_registry import (
    POLICY_SCHEMA_VERSION,
    REGISTRY_SCHEMA_VERSION,
    build_artifact_record,
    build_registry,
    git_provenance,
    load_versioning_policy,
    sha256_file,
)


class TestVersionRegistry(
    unittest.TestCase
):

    def test_schema_versions(self):

        self.assertEqual(
            POLICY_SCHEMA_VERSION,
            "greenpulse.versioning_policy.v1",
        )

        self.assertEqual(
            REGISTRY_SCHEMA_VERSION,
            "greenpulse.version_registry.v1",
        )


    def test_project_policy_valid(self):

        policy = load_versioning_policy(
            "configs/versioning_policy_v1.json"
        )

        self.assertEqual(
            policy[
                "mode"
            ],
            "MLOPS_LITE",
        )


    def test_full_mlflow_not_required(self):

        policy = load_versioning_policy(
            "configs/versioning_policy_v1.json"
        )

        self.assertFalse(
            policy[
                "full_mlflow_server_required"
            ]
        )


    def test_sha256_file(self):

        with tempfile.TemporaryDirectory() as tmp:

            path = (
                Path(
                    tmp
                )
                / "x.txt"
            )

            path.write_text(
                "greenpulse",
                encoding="utf-8",
            )

            value = sha256_file(
                path
            )


        self.assertEqual(
            len(
                value
            ),
            64,
        )


    def test_schema_version_not_promoted_to_trained_version(self):

        record = build_artifact_record(
            component_type="fusion_model",
            component_id="fusion",
            artifact_path=None,
            sha256=None,
            schema_version="greenpulse.multimodal_stress_fusion_model.v1",
            trained_model_version=None,
            status="SOFTWARE_FRAMEWORK",
        )

        self.assertIsNone(
            record[
                "trained_model_version"
            ]
        )


    def test_vision_operational_false_preserved(self):

        record = build_artifact_record(
            component_type="vision_model",
            component_id="tomato_clean_v1",
            artifact_path="model.onnx",
            sha256="a" * 64,
            status="RELEASE_CANDIDATE",
            operational_release_approved=False,
        )

        self.assertFalse(
            record[
                "operational_release_approved"
            ]
        )


    def test_invalid_hash_rejected(self):

        with self.assertRaises(
            ValueError
        ):

            build_artifact_record(
                component_type="dataset",
                component_id="dataset",
                artifact_path="x.json",
                sha256="bad",
                status="VERSIONED",
            )


    def test_non_git_directory_returns_no_commit(self):

        with tempfile.TemporaryDirectory() as tmp:

            result = git_provenance(
                tmp
            )


        self.assertFalse(
            result[
                "inside_repository"
            ]
        )

        self.assertIsNone(
            result[
                "commit"
            ]
        )


    def test_missing_git_blocks_release(self):

        components = [
            build_artifact_record(
                component_type=kind,
                component_id=kind,
                artifact_path=None,
                sha256=None,
                status="TEST",
                metrics=(
                    {
                        "test":
                            1.0
                    }
                    if kind
                    == "vision_model"
                    else None
                ),
            )
            for kind in (
                "vision_model",
                "fusion_model",
                "forecast_model",
                "dataset",
                "config",
                "api_schema",
                "system_release",
            )
        ]


        result = build_registry(
            system_release_id="test-release",
            components=components,
            git={
                "commit":
                    None
            },
        )


        self.assertFalse(
            result[
                "release_complete"
            ]
        )

        self.assertIn(
            "GIT_COMMIT_UNAVAILABLE",
            result[
                "blockers"
            ],
        )


    def test_complete_requirements_can_pass(self):

        components = [
            build_artifact_record(
                component_type=kind,
                component_id=kind,
                artifact_path=(
                    "artifact.bin"
                    if kind
                    != "system_release"
                    else None
                ),
                sha256=(
                    "b" * 64
                    if kind
                    != "system_release"
                    else None
                ),
                status="TEST",
                metrics=(
                    {
                        "metric":
                            1.0
                    }
                    if kind
                    == "vision_model"
                    else None
                ),
            )
            for kind in (
                "vision_model",
                "fusion_model",
                "forecast_model",
                "dataset",
                "config",
                "api_schema",
                "system_release",
            )
        ]


        result = build_registry(
            system_release_id="test-release",
            components=components,
            git={
                "commit":
                    "abc123"
            },
        )


        self.assertTrue(
            result[
                "release_complete"
            ]
        )


    def test_required_categories_guard(self):

        result = build_registry(
            system_release_id="test-release",
            components=[],
            git={
                "commit":
                    "abc123"
            },
        )


        self.assertFalse(
            result[
                "release_complete"
            ]
        )

        self.assertIn(
            "REQUIRED_COMPONENT_CATEGORY_MISSING",
            result[
                "blockers"
            ],
        )


    def test_claim_guards_present(self):

        result = build_registry(
            system_release_id="test-release",
            components=[],
            git={
                "commit":
                    None
            },
        )


        self.assertFalse(
            result[
                "claim_guards"
            ][
                "schema_version_is_trained_model_version"
            ]
        )

        self.assertFalse(
            result[
                "claim_guards"
            ][
                "missing_git_commit_fabricated"
            ]
        )


if __name__ == "__main__":
    unittest.main()