from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping

import json

from src.version_registry import (
    build_registry,
    sha256_file,
)


MANIFEST_SCHEMA_VERSION = (
    "greenpulse.system_release_manifest.v1"
)


def _require_nonempty_string(
    value: Any,
    name: str,
) -> str:

    if (
        not isinstance(
            value,
            str,
        )
        or not value.strip()
    ):

        raise ValueError(
            f"{name} must be a non-empty string."
        )


    return value.strip()


def _normalize_metrics_sources(
    metrics_sources: list[
        Mapping[
            str,
            Any,
        ]
    ],
) -> list[dict[str, Any]]:

    if not isinstance(
        metrics_sources,
        list,
    ):

        raise ValueError(
            "metrics_sources must be a list."
        )


    normalized = []


    for item in metrics_sources:

        if not isinstance(
            item,
            Mapping,
        ):

            raise ValueError(
                "Every metrics source must be a mapping."
            )


        path = _require_nonempty_string(
            item.get(
                "path"
            ),
            "metrics source path",
        )


        sha256 = item.get(
            "sha256"
        )


        if (
            not isinstance(
                sha256,
                str,
            )
            or len(
                sha256
            )
            != 64
        ):

            raise ValueError(
                "Metrics source sha256 must be 64 characters."
            )


        normalized.append(
            {
                "path":
                    path,

                "sha256":
                    sha256,
            }
        )


    return normalized


def build_release_manifest(
    *,
    system_release_id: str,
    release_status: str,
    components: list[
        Mapping[
            str,
            Any,
        ]
    ],
    git: Mapping[
        str,
        Any,
    ],
    metrics_sources: list[
        Mapping[
            str,
            Any,
        ]
    ],
) -> dict[str, Any]:

    release_id = _require_nonempty_string(
        system_release_id,
        "system_release_id",
    )

    status = _require_nonempty_string(
        release_status,
        "release_status",
    )


    registry = build_registry(
        system_release_id=release_id,
        components=[
            deepcopy(
                dict(
                    component
                )
            )
            for component in components
        ],
        git=dict(
            git
        ),
    )


    normalized_metrics = (
        _normalize_metrics_sources(
            metrics_sources
        )
    )


    metrics_sources_present = bool(
        normalized_metrics
    )


    blockers = list(
        registry[
            "blockers"
        ]
    )


    if not metrics_sources_present:

        blockers.append(
            "METRICS_SOURCE_ARTIFACT_MISSING"
        )


    blockers = list(
        dict.fromkeys(
            blockers
        )
    )


    release_complete = all(
        (
            registry[
                "release_complete"
            ],
            metrics_sources_present,
        )
    )


    return {
        "schema_version":
            MANIFEST_SCHEMA_VERSION,

        "system_release_id":
            release_id,

        "release_status":
            status,

        "registry":
            registry,

        "metrics_sources":
            normalized_metrics,

        "release_checks": {
            "required_component_categories_present":
                registry[
                    "release_checks"
                ][
                    "required_categories_present"
                ],

            "git_commit_present":
                registry[
                    "release_checks"
                ][
                    "git_commit_present"
                ],

            "file_hashes_present":
                registry[
                    "release_checks"
                ][
                    "file_hashes_present"
                ],

            "component_metrics_present":
                registry[
                    "release_checks"
                ][
                    "metrics_present"
                ],

            "metrics_source_artifacts_present":
                metrics_sources_present,
        },

        "release_complete":
            release_complete,

        "blockers":
            blockers,

        "claim_guards": {
            "draft_manifest_equals_complete_release":
                False,

            "schema_version_equals_trained_model_version":
                False,

            "release_candidate_equals_operational_release":
                False,

            "release_candidate_equals_hailo_approved":
                False,

            "missing_git_commit_fabricated":
                False,
        },
    }


def verify_release_artifacts(
    manifest: Mapping[
        str,
        Any,
    ],
    *,
    root: Any,
) -> dict[str, Any]:

    if not isinstance(
        manifest,
        Mapping,
    ):

        raise ValueError(
            "manifest must be a mapping."
        )


    root = Path(
        root
    )


    records = []


    registry = manifest.get(
        "registry"
    )


    if not isinstance(
        registry,
        Mapping,
    ):

        raise ValueError(
            "registry missing."
        )


    components = registry.get(
        "components"
    )


    if not isinstance(
        components,
        list,
    ):

        raise ValueError(
            "registry components missing."
        )


    for component in components:

        artifact_path = component.get(
            "artifact_path"
        )

        expected_sha = component.get(
            "sha256"
        )


        if artifact_path is None:

            continue


        path = (
            root
            / artifact_path
        )


        exists = path.is_file()


        actual_sha = (
            sha256_file(
                path
            )
            if exists
            else None
        )


        matches = (
            exists
            and expected_sha
            is not None
            and actual_sha
            == expected_sha
        )


        records.append(
            {
                "component_type":
                    component.get(
                        "component_type"
                    ),

                "component_id":
                    component.get(
                        "component_id"
                    ),

                "artifact_path":
                    artifact_path,

                "exists":
                    exists,

                "expected_sha256":
                    expected_sha,

                "actual_sha256":
                    actual_sha,

                "sha256_matches":
                    matches,
            }
        )


    metrics = manifest.get(
        "metrics_sources"
    )


    if not isinstance(
        metrics,
        list,
    ):

        raise ValueError(
            "metrics_sources missing."
        )


    metrics_records = []


    for item in metrics:

        path = (
            root
            / item[
                "path"
            ]
        )


        exists = path.is_file()


        actual_sha = (
            sha256_file(
                path
            )
            if exists
            else None
        )


        metrics_records.append(
            {
                "path":
                    item[
                        "path"
                    ],

                "exists":
                    exists,

                "expected_sha256":
                    item[
                        "sha256"
                    ],

                "actual_sha256":
                    actual_sha,

                "sha256_matches":
                    (
                        exists
                        and actual_sha
                        == item[
                            "sha256"
                        ]
                    ),
            }
        )


    all_component_artifacts_match = all(
        row[
            "sha256_matches"
        ]
        for row in records
    )


    all_metrics_sources_match = all(
        row[
            "sha256_matches"
        ]
        for row in metrics_records
    )


    return {
        "schema_version":
            "greenpulse.system_release_artifact_verification.v1",

        "component_artifacts":
            records,

        "metrics_sources":
            metrics_records,

        "all_component_artifacts_match":
            all_component_artifacts_match,

        "all_metrics_sources_match":
            all_metrics_sources_match,

        "all_verified":
            (
                all_component_artifacts_match
                and all_metrics_sources_match
            ),
    }


def write_release_manifest(
    manifest: Mapping[
        str,
        Any,
    ],
    path: Any,
) -> Path:

    if not isinstance(
        manifest,
        Mapping,
    ):

        raise ValueError(
            "manifest must be a mapping."
        )


    if (
        manifest.get(
            "schema_version"
        )
        != MANIFEST_SCHEMA_VERSION
    ):

        raise ValueError(
            "Unexpected manifest schema."
        )


    output = Path(
        path
    )


    if output.exists():

        raise FileExistsError(
            str(
                output
            )
        )


    if not output.parent.is_dir():

        raise FileNotFoundError(
            "Output parent directory does not exist."
        )


    output.write_text(
        json.dumps(
            dict(
                manifest
            ),
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


    return output