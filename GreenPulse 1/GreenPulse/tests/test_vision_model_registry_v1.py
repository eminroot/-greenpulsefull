
import copy
import hashlib
import json
import tempfile
import unittest

from pathlib import Path

from src.vision_model_registry import (
    resolve_diagnostic_model
)


def digest(content):
    return hashlib.sha256(
        content
    ).hexdigest()


class RegistryTests(unittest.TestCase):

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)

        self.root = Path(temp.name)

        models = {}

        for crop, classes in (
            ("tomato", 10),
            ("bell_pepper", 2)
        ):
            entries = {}

            for extension in ("pt", "onnx"):
                filename = (
                    crop + "." + extension
                )

                data = filename.encode()
                path = self.root / filename

                path.write_bytes(data)

                entries[
                    "pytorch"
                    if extension == "pt"
                    else "onnx"
                ] = {
                    "path": filename,
                    "sha256": digest(data)
                }

            names = (
                ["t" + str(i) for i in range(10)]
                if crop == "tomato"
                else ["bacterial_spot", "healthy"]
            )

            models[crop] = {
                "crop": crop,
                "class_count": classes,
                "class_names": names,
                **entries,
                "evidence": [],
                "operational_release_approved": False
            }

        self.registry = {
            "version": "1.0",
            "mode": "RESEARCH_ONLY",
            "crop_identity_source":
                "UNVERIFIED_EXTERNAL_CLAIM",
            "unknown_crop_policy": "ABSTAIN",
            "actuation_authorized": False,
            "models": models
        }

        self.path = (
            self.root / "registry.json"
        )

        self.save()

    def save(self):
        self.path.write_text(
            json.dumps(self.registry),
            encoding="utf-8"
        )

    def resolve(self, crop):
        return resolve_diagnostic_model(
            crop,
            registry_path=self.path,
            project_root=self.root
        )

    def test_01_tomato_research_only(self):
        result = self.resolve("tomato")

        self.assertEqual(
            result["status"],
            "RESEARCH_MODEL_AVAILABLE"
        )

        self.assertFalse(
            result["physical_actuation_allowed"]
        )

        self.assertFalse(
            result["crop_identity_verified"]
        )

    def test_02_pepper_research_only(self):
        result = self.resolve("bell_pepper")

        self.assertEqual(
            result["status"],
            "RESEARCH_MODEL_AVAILABLE"
        )

        self.assertFalse(
            result["autonomous_actuation_allowed"]
        )

    def test_03_apple_blocked(self):
        self.assertEqual(
            self.resolve("apple")["status"],
            "BLOCKED"
        )

    def test_04_cucumber_not_ready(self):
        self.assertEqual(
            self.resolve("cucumber")["status"],
            "BLOCKED"
        )

    def test_05_tampered_checkpoint(self):
        path = self.root / "tomato.pt"

        path.write_bytes(b"tampered")

        self.assertEqual(
            self.resolve("tomato")["status"],
            "BLOCKED"
        )

    def test_06_unsafe_artifact_path(self):
        self.registry["models"]["tomato"][
            "pytorch"
        ]["path"] = "../outside.pt"

        self.save()

        self.assertEqual(
            self.resolve("tomato")["status"],
            "BLOCKED"
        )

    def test_07_unsafe_operational_flag(self):
        self.registry[
            "actuation_authorized"
        ] = True

        self.save()

        self.assertEqual(
            self.resolve("tomato")["status"],
            "BLOCKED"
        )

    def test_08_tampered_evidence(self):
        evidence = self.root / "evidence.json"

        evidence.write_bytes(b"original")

        self.registry["models"][
            "bell_pepper"
        ]["evidence"] = [{
            "path": "evidence.json",
            "sha256": digest(b"original")
        }]

        self.save()

        evidence.write_bytes(b"modified")

        self.assertEqual(
            self.resolve("bell_pepper")["status"],
            "BLOCKED"
        )


if __name__ == "__main__":
    unittest.main()
