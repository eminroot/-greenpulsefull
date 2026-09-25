
import hashlib
import json
import re

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_REGISTRY = (
    ROOT / "configs/vision_model_registry_v1.json"
)

SUPPORTED = {
    "tomato": 10,
    "bell_pepper": 2
}


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b""
        ):
            digest.update(chunk)

    return digest.hexdigest()


def blocked(reason):
    return {
        "status": "BLOCKED",
        "reason": reason,
        "diagnostic_model_available": False,
        "crop_identity_verified": False,
        "autonomous_actuation_allowed": False,
        "physical_actuation_allowed": False
    }


def verified_file(root, record):
    if not isinstance(record, dict):
        raise ValueError("Invalid artifact.")

    if set(record) != {"path", "sha256"}:
        raise ValueError("Invalid artifact fields.")

    digest = record["sha256"]
    relative = Path(record["path"])

    if (
        not isinstance(digest, str)
        or re.fullmatch(
            r"[0-9a-f]{64}",
            digest
        ) is None
    ):
        raise ValueError("Invalid SHA-256.")

    if relative.is_absolute():
        raise ValueError("Absolute path forbidden.")

    path = (root / relative).resolve()

    if not path.is_relative_to(root):
        raise ValueError(
            "Artifact escapes project."
        )

    if not path.is_file():
        raise FileNotFoundError(path)

    if sha256_file(path) != digest:
        raise ValueError(
            "Artifact integrity mismatch."
        )

    return path


def resolve_diagnostic_model(
    crop,
    registry_path=None,
    project_root=None
):
    """
    Resolve a research model by an externally
    supplied, UNVERIFIED crop claim.

    No crop recognition is performed here.
    No operational decision is authorized.
    """

    if crop not in SUPPORTED:
        return blocked("UNSUPPORTED_CROP")

    root = (
        Path(project_root).resolve()
        if project_root is not None
        else ROOT.resolve()
    )

    registry_file = (
        Path(registry_path).resolve()
        if registry_path is not None
        else DEFAULT_REGISTRY.resolve()
    )

    try:
        registry = json.loads(
            registry_file.read_text(
                encoding="utf-8-sig"
            )
        )

        if registry.get("version") != "1.0":
            raise ValueError("Invalid version.")

        if registry.get("mode") != "RESEARCH_ONLY":
            raise ValueError("Unsafe registry mode.")

        if registry.get(
            "actuation_authorized"
        ) is not False:
            raise ValueError(
                "Unsafe actuation setting."
            )

        if registry.get(
            "crop_identity_source"
        ) != "UNVERIFIED_EXTERNAL_CLAIM":
            raise ValueError(
                "Invalid identity policy."
            )

        if registry.get(
            "unknown_crop_policy"
        ) != "ABSTAIN":
            raise ValueError(
                "Unsafe unknown-crop policy."
            )

        models = registry["models"]

        if set(models) != set(SUPPORTED):
            raise ValueError(
                "Unexpected crop registration."
            )

        model = models[crop]

        if model["crop"] != crop:
            raise ValueError(
                "Crop mapping mismatch."
            )

        if model["class_count"] != SUPPORTED[crop]:
            raise ValueError(
                "Class count mismatch."
            )

        classes = model["class_names"]

        if (
            not isinstance(classes, list)
            or len(classes) != SUPPORTED[crop]
            or len(classes) != len(set(classes))
        ):
            raise ValueError(
                "Invalid class mapping."
            )

        pt = verified_file(
            root,
            model["pytorch"]
        )

        onnx = verified_file(
            root,
            model["onnx"]
        )

        for evidence in model["evidence"]:
            verified_file(root, evidence)

        if model.get(
            "operational_release_approved"
        ) is not False:
            raise ValueError(
                "Unsafe model release status."
            )

    except (
        OSError,
        ValueError,
        KeyError,
        TypeError
    ):
        return blocked(
            "REGISTRY_OR_ARTIFACT_VERIFICATION_FAILED"
        )

    return {
        "status": "RESEARCH_MODEL_AVAILABLE",
        "crop_claim": crop,
        "crop_identity_verified": False,
        "class_names": classes,
        "pytorch_path": str(pt),
        "onnx_path": str(onnx),
        "diagnostic_model_available": True,
        "autonomous_actuation_allowed": False,
        "physical_actuation_allowed": False,
        "warning": (
            "Crop identity is an unverified claim. "
            "Model availability is not evidence of "
            "real-greenhouse performance."
        )
    }
