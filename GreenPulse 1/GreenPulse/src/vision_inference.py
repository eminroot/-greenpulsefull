import csv
import json
import hashlib

from pathlib import Path
from ultralytics import YOLO

MODEL_PATH = Path(
    "models/greenpulse_tomato_yolo11n_cls_v1.0.onnx"
)

RELEASE_PATH = Path(
    "models/tomato_v1_release.json"
)


def sha256(path):
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()


class GreenPulseVision:

    def __init__(self):

        self.release = json.loads(
            RELEASE_PATH.read_text(encoding="utf-8")
        )

        expected_hash = self.release["onnx"]["sha256"]

        if sha256(MODEL_PATH) != expected_hash:
            raise RuntimeError("MODEL INTEGRITY ERROR")

        self.model = YOLO(
            str(MODEL_PATH),
            task="classify"
        )

        actual_classes = [
            self.model.names[i]
            for i in sorted(self.model.names)
        ]

        if actual_classes != self.release["classes"]:
            raise RuntimeError("MODEL CLASS MISMATCH")

        print("GREENPULSE VISION ENGINE READY")

    def predict(self, image_path, crop):

        if crop != "tomato":
            return {
                "status": "UNSUPPORTED_CROP",
                "decision": "NO_AUTONOMOUS_ACTION"
            }

        image_path = Path(image_path)

        if not image_path.is_file():
            raise FileNotFoundError(image_path)

        results = self.model.predict(
            source=str(image_path),
            imgsz=224,
            device="cpu",
            verbose=False
        )

        result = results[0]

        if result.probs is None:
            raise RuntimeError("INVALID MODEL OUTPUT")

        class_id = int(result.probs.top1)

        label = self.model.names[class_id]

        confidence = float(
            result.probs.top1conf.item()
        )

        if label == "Tomato___healthy":
            state = "VISUALLY_HEALTHY"
        else:
            state = "DISEASE_PATTERN_PREDICTED"

        return {
            "schema_version": "1.0",
            "status": "SUCCESS",
            "crop": crop,
            "vision": {
                "state": state,
                "predicted_class": label,
                "confidence": round(confidence, 6),
                "confidence_calibrated": False
            },
            "water_stress_risk": None,
            "forecast": None,
            "decision": "NO_AUTONOMOUS_ACTION",
            "model": {
                "version": self.release["version"],
                "format": "ONNX",
                "sha256": self.release["onnx"]["sha256"]
            }
        }


if __name__ == "__main__":

    manifest = Path(
        "reports/tomato_split_v1/validation.csv"
    )

    with open(manifest, encoding="utf-8") as f:
        sample = next(csv.DictReader(f))

    engine = GreenPulseVision()

    prediction = engine.predict(
        image_path=sample["image_path"],
        crop="tomato"
    )

    print("\nGREENPULSE INFERENCE RESULT")
    print("-------------------------------")

    print(json.dumps(
        prediction,
        indent=4,
        ensure_ascii=False
    ))
