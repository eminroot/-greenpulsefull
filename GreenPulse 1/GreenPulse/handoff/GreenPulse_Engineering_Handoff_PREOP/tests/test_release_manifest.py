import json
import tempfile
import unittest
from pathlib import Path

from src.release_manifest import (
    MANIFEST_SCHEMA_VERSION,
    build_release_manifest,
    verify_release_artifacts,
    write_release_manifest,
)

from src.version_registry import (
    build_artifact_record,
    sha256_file,
)


def component_set(
    *,
    artifact_path=None,
    artifact_sha=None,
):

    components = []


    for kind in (
        "vision_model",
        "fusion_model",
        "forecast_model",
        "dataset",
        "config",
        "api_schema",
        "system_release",
    ):

        components.append(
            build_artifact_record(
                component_type=kind,
                component_id=kind,
                artifact_path=(
                    artifact_path
                    if kind
                    == "vision_model"
                    else None
                ),
                sha256=(
                    artifact_sha
                    if kind
                    == "vision_model"
                    else None
                ),
                status="TEST_ONLY",
                metrics=(
                    {
                        "accuracy":
                            0.9
                    }
                    if kind
                    == "vision_model"
                    else None
                ),
            )
        )


    return components


class TestReleaseManifest(
    unittest.TestCase
):

    def test_schema_version(self):

        self.assertEqual(
            MANIFEST_SCHEMA_VERSION,
            "greenpulse.system_release_manifest.v1",
        )


    def test_missing_git_keeps_release_incomplete(self):

        manifest = build_release_manifest(
            system_release_id="test-release",
            release_status="DRAFT",
            components=component_set(),
            git={
                "commit":
                    None,
            },
            metrics_sources=[
                {
                    "path":
                        "metrics.json",

                    "sha256":
                        "a" * 64,
                }
            ],
        )


        self.assertFalse(
            manifest[
                "release_complete"
            ]
        )

        self.assertIn(
            "GIT_COMMIT_UNAVAILABLE",
            manifest[
                "blockers"
            ],
        )


    def test_complete_inputs_can_pass_release_gate(self):

        manifest = build_release_manifest(
            system_release_id="test-release",
            release_status="COMPLETE",
            components=component_set(),
            git={
                "commit":
                    "abc123",
            },
            metrics_sources=[
                {
                    "path":
                        "metrics.json",

                    "sha256":
                        "a" * 64,
                }
            ],
        )


        self.assertTrue(
            manifest[
                "release_complete"
            ]
        )


    def test_metrics_source_required(self):

        manifest = build_release_manifest(
            system_release_id="test-release",
            release_status="DRAFT",
            components=component_set(),
            git={
                "commit":
                    "abc123",
            },
            metrics_sources=[],
        )


        self.assertFalse(
            manifest[
                "release_complete"
            ]
        )

        self.assertIn(
            "METRICS_SOURCE_ARTIFACT_MISSING",
            manifest[
                "blockers"
            ],
        )


    def test_claim_guards_present(self):

        manifest = build_release_manifest(
            system_release_id="test-release",
            release_status="DRAFT",
            components=component_set(),
            git={
                "commit":
                    None,
            },
            metrics_sources=[],
        )


        guards = manifest[
            "claim_guards"
        ]


        self.assertFalse(
            guards[
                "draft_manifest_equals_complete_release"
            ]
        )

        self.assertFalse(
            guards[
                "release_candidate_equals_hailo_approved"
            ]
        )

        self.assertFalse(
            guards[
                "missing_git_commit_fabricated"
            ]
        )


    def test_manifest_does_not_promote_schema_to_model_version(self):

        component = build_artifact_record(
            component_type="fusion_model",
            component_id="fusion",
            artifact_path=None,
            sha256=None,
            schema_version="greenpulse.multimodal_stress_fusion_model.v1",
            trained_model_version=None,
            status="SOFTWARE_FRAMEWORK",
        )


        components = component_set()

        components[
            1
        ] = component


        manifest = build_release_manifest(
            system_release_id="test-release",
            release_status="DRAFT",
            components=components,
            git={
                "commit":
                    None,
            },
            metrics_sources=[],
        )


        fusion = manifest[
            "registry"
        ][
            "components"
        ][1]


        self.assertIsNone(
            fusion[
                "trained_model_version"
            ]
        )


    def test_write_manifest(self):

        manifest = build_release_manifest(
            system_release_id="test-release",
            release_status="DRAFT",
            components=component_set(),
            git={
                "commit":
                    None,
            },
            metrics_sources=[],
        )


        with tempfile.TemporaryDirectory() as tmp:

            output = (
                Path(
                    tmp
                )
                / "manifest.json"
            )


            write_release_manifest(
                manifest,
                output,
            )


            loaded = json.loads(
                output.read_text(
                    encoding="utf-8"
                )
            )


        self.assertEqual(
            loaded[
                "schema_version"
            ],
            MANIFEST_SCHEMA_VERSION,
        )


    def test_existing_manifest_not_overwritten(self):

        manifest = build_release_manifest(
            system_release_id="test-release",
            release_status="DRAFT",
            components=component_set(),
            git={
                "commit":
                    None,
            },
            metrics_sources=[],
        )


        with tempfile.TemporaryDirectory() as tmp:

            output = (
                Path(
                    tmp
                )
                / "manifest.json"
            )

            output.write_text(
                "{}",
                encoding="utf-8",
            )


            with self.assertRaises(
                FileExistsError
            ):

                write_release_manifest(
                    manifest,
                    output,
                )


    def test_component_artifact_verification_passes(self):

        with tempfile.TemporaryDirectory() as tmp:

            root = Path(
                tmp
            )

            artifact = (
                root
                / "model.bin"
            )

            metric = (
                root
                / "metrics.json"
            )


            artifact.write_bytes(
                b"model"
            )

            metric.write_text(
                '{"accuracy": 1.0}',
                encoding="utf-8",
            )


            components = component_set(
                artifact_path="model.bin",
                artifact_sha=sha256_file(
                    artifact
                ),
            )


            manifest = build_release_manifest(
                system_release_id="test-release",
                release_status="DRAFT",
                components=components,
                git={
                    "commit":
                        None,
                },
                metrics_sources=[
                    {
                        "path":
                            "metrics.json",

                        "sha256":
                            sha256_file(
                                metric
                            ),
                    }
                ],
            )


            result = verify_release_artifacts(
                manifest,
                root=root,
            )


        self.assertTrue(
            result[
                "all_verified"
            ]
        )


    def test_component_hash_mismatch_detected(self):

        with tempfile.TemporaryDirectory() as tmp:

            root = Path(
                tmp
            )

            artifact = (
                root
                / "model.bin"
            )

            metric = (
                root
                / "metrics.json"
            )


            artifact.write_bytes(
                b"model"
            )

            metric.write_text(
                "{}",
                encoding="utf-8",
            )


            components = component_set(
                artifact_path="model.bin",
                artifact_sha="0" * 64,
            )


            manifest = build_release_manifest(
                system_release_id="test-release",
                release_status="DRAFT",
                components=components,
                git={
                    "commit":
                        None,
                },
                metrics_sources=[
                    {
                        "path":
                            "metrics.json",

                        "sha256":
                            sha256_file(
                                metric
                            ),
                    }
                ],
            )


            result = verify_release_artifacts(
                manifest,
                root=root,
            )


        self.assertFalse(
            result[
                "all_component_artifacts_match"
            ]
        )

        self.assertFalse(
            result[
                "all_verified"
            ]
        )


    def test_missing_artifact_detected(self):

        manifest = build_release_manifest(
            system_release_id="test-release",
            release_status="DRAFT",
            components=component_set(
                artifact_path="missing.bin",
                artifact_sha="a" * 64,
            ),
            git={
                "commit":
                    None,
            },
            metrics_sources=[],
        )


        with tempfile.TemporaryDirectory() as tmp:

            result = verify_release_artifacts(
                manifest,
                root=tmp,
            )


        self.assertFalse(
            result[
                "all_component_artifacts_match"
            ]
        )


    def test_metrics_hash_mismatch_detected(self):

        with tempfile.TemporaryDirectory() as tmp:

            root = Path(
                tmp
            )

            metric = (
                root
                / "metrics.json"
            )

            metric.write_text(
                "{}",
                encoding="utf-8",
            )


            manifest = build_release_manifest(
                system_release_id="test-release",
                release_status="DRAFT",
                components=component_set(),
                git={
                    "commit":
                        None,
                },
                metrics_sources=[
                    {
                        "path":
                            "metrics.json",

                        "sha256":
                            "f" * 64,
                    }
                ],
            )


            result = verify_release_artifacts(
                manifest,
                root=root,
            )


        self.assertFalse(
            result[
                "all_metrics_sources_match"
            ]
        )


    def test_system_release_id_required(self):

        with self.assertRaises(
            ValueError
        ):

            build_release_manifest(
                system_release_id="",
                release_status="DRAFT",
                components=component_set(),
                git={
                    "commit":
                        None,
                },
                metrics_sources=[],
            )


if __name__ == "__main__":
    unittest.main()