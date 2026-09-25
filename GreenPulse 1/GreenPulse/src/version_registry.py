from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

import hashlib
import json
import shutil
import subprocess


REGISTRY_SCHEMA_VERSION = (
    "greenpulse.version_registry.v1"
)

POLICY_SCHEMA_VERSION = (
    "greenpulse.versioning_policy.v1"
)


ALLOWED_COMPONENT_TYPES = {
    "vision_model",
    "fusion_model",
    "forecast_model",
    "dataset",
    "config",
    "api_schema",
    "system_release",
}


def sha256_file(
    path: Any,
) -> str:

    target = Path(
        path
    )


    if not target.is_file():

        raise FileNotFoundError(
            str(
                target
            )
        )


    h = hashlib.sha256()


    with target.open(
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


def load_versioning_policy(
    path: Any,
) -> dict[str, Any]:

    policy = json.loads(
        Path(
            path
        ).read_text(
            encoding="utf-8-sig"
        )
    )


    validate_versioning_policy(
        policy
    )


    return policy


def validate_versioning_policy(
    policy: Mapping[
        str,
        Any,
    ],
) -> None:

    if not isinstance(
        policy,
        Mapping,
    ):

        raise ValueError(
            "Versioning policy must be a mapping."
        )


    if (
        policy.get(
            "schema_version"
        )
        != POLICY_SCHEMA_VERSION
    ):

        raise ValueError(
            "Unsupported versioning policy schema."
        )


    if (
        policy.get(
            "mode"
        )
        != "MLOPS_LITE"
    ):

        raise ValueError(
            "Expected MLOPS_LITE mode."
        )


    if (
        policy.get(
            "full_mlflow_server_required"
        )
        is not False
    ):

        raise ValueError(
            "Full MLflow server must not be required."
        )


    required = policy.get(
        "required_component_categories"
    )


    if (
        not isinstance(
            required,
            list,
        )
        or set(
            required
        )
        != ALLOWED_COMPONENT_TYPES
    ):

        raise ValueError(
            "Required component categories invalid."
        )


    release_requirements = policy.get(
        "release_requirements"
    )


    if not isinstance(
        release_requirements,
        Mapping,
    ):

        raise ValueError(
            "release_requirements missing."
        )


    for field in (
        "git_commit_required",
        "metrics_required",
        "file_hashes_required",
    ):

        if (
            release_requirements.get(
                field
            )
            is not True
        ):

            raise ValueError(
                f"{field} must be true."
            )


    guards = policy.get(
        "claim_guards"
    )


    if not isinstance(
        guards,
        Mapping,
    ):

        raise ValueError(
            "claim_guards missing."
        )


    for field in (
        "schema_version_equals_trained_model_version",
        "onnx_exists_equals_operational_release",
        "release_candidate_equals_hailo_approved",
        "missing_git_commit_may_be_fabricated",
    ):

        if (
            guards.get(
                field
            )
            is not False
        ):

            raise ValueError(
                f"{field} must remain false."
            )


def git_provenance(
    root: Any,
) -> dict[str, Any]:

    root = Path(
        root
    )


    if (
        shutil.which(
            "git"
        )
        is None
    ):

        return {
            "git_available":
                False,

            "inside_repository":
                False,

            "commit":
                None,

            "branch":
                None,

            "working_tree_dirty":
                None,
        }


    def run(
        *args,
    ):

        result = subprocess.run(
            [
                "git",
                *args,
            ],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )

        return (
            result.returncode,
            result.stdout.strip(),
        )


    rc, value = run(
        "rev-parse",
        "--is-inside-work-tree",
    )


    inside = (
        rc == 0
        and value.lower()
        == "true"
    )


    if not inside:

        return {
            "git_available":
                True,

            "inside_repository":
                False,

            "commit":
                None,

            "branch":
                None,

            "working_tree_dirty":
                None,
        }


    rc, commit = run(
        "rev-parse",
        "HEAD",
    )


    if rc != 0:

        commit = None


    rc, branch = run(
        "branch",
        "--show-current",
    )


    if rc != 0:

        branch = None


    rc, status = run(
        "status",
        "--porcelain",
    )


    dirty = (
        bool(
            status
        )
        if rc == 0
        else None
    )


    return {
        "git_available":
            True,

        "inside_repository":
            True,

        "commit":
            commit,

        "branch":
            branch,

        "working_tree_dirty":
            dirty,
    }


def build_artifact_record(
    *,
    component_type: str,
    component_id: str,
    artifact_path: Optional[str],
    sha256: Optional[str],
    schema_version: Optional[str] = None,
    trained_model_version: Optional[str] = None,
    status: str,
    operational_release_approved: Optional[bool] = None,
    metrics: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:

    if component_type not in ALLOWED_COMPONENT_TYPES:

        raise ValueError(
            "Unsupported component_type."
        )


    if (
        not isinstance(
            component_id,
            str,
        )
        or not component_id.strip()
    ):

        raise ValueError(
            "component_id is required."
        )


    if (
        sha256 is not None
        and (
            not isinstance(
                sha256,
                str,
            )
            or len(
                sha256
            )
            != 64
        )
    ):

        raise ValueError(
            "sha256 must be a 64-character hash or null."
        )


    if (
        operational_release_approved
        is not None
        and type(
            operational_release_approved
        )
        is not bool
    ):

        raise ValueError(
            "operational_release_approved must be bool or null."
        )


    return {
        "component_type":
            component_type,

        "component_id":
            component_id.strip(),

        "artifact_path":
            artifact_path,

        "sha256":
            sha256,

        "schema_version":
            schema_version,

        "trained_model_version":
            trained_model_version,

        "status":
            status,

        "operational_release_approved":
            operational_release_approved,

        "metrics":
            (
                dict(
                    metrics
                )
                if metrics is not None
                else None
            ),
    }


def build_registry(
    *,
    system_release_id: str,
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
) -> dict[str, Any]:

    if (
        not isinstance(
            system_release_id,
            str,
        )
        or not system_release_id.strip()
    ):

        raise ValueError(
            "system_release_id is required."
        )


    if not isinstance(
        components,
        list,
    ):

        raise ValueError(
            "components must be a list."
        )


    normalized = [
        dict(
            component
        )
        for component in components
    ]


    categories = {
        component.get(
            "component_type"
        )
        for component in normalized
    }


    git_commit = git.get(
        "commit"
    )


    hashes_present = all(
        (
            component.get(
                "sha256"
            )
            is not None
        )
        for component in normalized
        if component.get(
            "artifact_path"
        )
        is not None
    )


    metrics_present = any(
        component.get(
            "metrics"
        )
        is not None
        for component in normalized
    )


    required_categories_present = (
        ALLOWED_COMPONENT_TYPES
        .issubset(
            categories
        )
    )


    release_complete = all(
        (
            required_categories_present,
            bool(
                git_commit
            ),
            hashes_present,
            metrics_present,
        )
    )


    blockers = []


    if not required_categories_present:

        blockers.append(
            "REQUIRED_COMPONENT_CATEGORY_MISSING"
        )


    if not git_commit:

        blockers.append(
            "GIT_COMMIT_UNAVAILABLE"
        )


    if not hashes_present:

        blockers.append(
            "FILE_HASH_MISSING"
        )


    if not metrics_present:

        blockers.append(
            "RELEASE_METRICS_MISSING"
        )


    return {
        "schema_version":
            REGISTRY_SCHEMA_VERSION,

        "system_release_id":
            system_release_id.strip(),

        "git":
            dict(
                git
            ),

        "components":
            normalized,

        "release_checks": {
            "required_categories_present":
                required_categories_present,

            "git_commit_present":
                bool(
                    git_commit
                ),

            "file_hashes_present":
                hashes_present,

            "metrics_present":
                metrics_present,
        },

        "release_complete":
            release_complete,

        "blockers":
            blockers,

        "claim_guards": {
            "schema_version_is_trained_model_version":
                False,

            "onnx_artifact_implies_operational_release":
                False,

            "missing_git_commit_fabricated":
                False,
        },
    }