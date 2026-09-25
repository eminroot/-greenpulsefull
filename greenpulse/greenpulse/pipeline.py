"""
GreenPulse End-to-End Pipeline (Layer 1-6)
----------------------------------------------------------------
Hesabatdakı "Optimizə Edilmiş Yeni ML Arxitekturası"nı tam orkestrasiya edir:

    Layer 1  Unified Ingestion & HAL
    Layer 2  Leaf Vision AI Engine        (YOLOv11n-Seg)
    Layer 3  Biomorphic Feature Extraction (HSV)
    Layer 4  Digital Twin Sensor Fusion    (LoRaWAN simulyasiyası)
    Layer 5  GPSS Engine                   (0-100 stress skoru)
    Layer 6  Autonomous Decision Engine

Layer 7 (Streamlit Dashboard) BU modulun `run()` metodunu çağırır — heç vaxt
ayrı-ayrı qatlarla birbaşa danışmır. Bu tək giriş nöqtəsi özü də HAL
prinsipinin davamıdır: UI pipeline-ın daxili implementasiyasını bilməməlidir.
"""

import time
import numpy as np

from hal import SensorReading, get_sensor_source
from vision_engine import LeafVisionEngine
from biomorphic import analyze as biomorphic_analyze
from digital_twin import fuse as digital_twin_fuse
from gpss_engine import compute as gpss_compute
from decision_engine import decide
from edge_monitor import get_resource_snapshot


class GreenPulsePipeline:
    def __init__(self, weights_path: str = "models/yolo11n-seg.pt", device: str = "cpu"):
        self.vision_engine = LeafVisionEngine(weights_path=weights_path, device=device)

    def run(self, image_bgr: np.ndarray, sensor_reading: SensorReading = None,
             sensor_mode: str = "simulated", scenario: str = "normal") -> dict:

        t_start = time.perf_counter()

        # Layer 1: HAL üzərindən sensor datası al (çağıran artıq reading verməyibsə)
        if sensor_reading is None:
            source = get_sensor_source(mode=sensor_mode, scenario=scenario)
            sensor_reading = source.read()

        # Layer 2: vision inference
        vision_result = self.vision_engine.predict(image_bgr)

        # Layer 3: yarpaq maskası daxilində HSV / biomorfik analiz
        bio_result = biomorphic_analyze(image_bgr, vision_result.leaf_mask, vision_result.damage_mask)

        # Layer 4: sensor fusion + LoRaWAN simulyasiyası
        fused = digital_twin_fuse(sensor_reading)

        # Layer 5: GPSS stress skoru
        gpss_result = gpss_compute(
            damage_percentage=bio_result.damage_percentage,
            soil_moisture=sensor_reading.soil_moisture,
            temperature=sensor_reading.temperature,
            humidity=sensor_reading.humidity,
            light=sensor_reading.light,
        )

        # Layer 6: avtonom qərar
        decision = decide(gpss_result.gpss_score, gpss_result.stress_type)

        total_latency_ms = (time.perf_counter() - t_start) * 1000.0
        resources = get_resource_snapshot()

        # Final sxem — hesabatdakı "Demo JSON Çıxış Nümunəsi" ilə tam üst-üstə düşür.
        return {
            "stress_type": gpss_result.stress_type,
            "confidence": round(float(vision_result.confidence), 2),
            "damage_percentage": round(bio_result.damage_percentage, 1),
            "soil_moisture": sensor_reading.soil_moisture,
            "temperature": sensor_reading.temperature,
            "humidity": sensor_reading.humidity,
            "light": sensor_reading.light,
            "gpss_score": gpss_result.gpss_score,
            "risk_level": gpss_result.risk_level,
            "decision": decision.decision,
            "inference_latency_ms": round(vision_result.inference_ms, 1),
            "edge_cpu_usage_pct": resources["edge_cpu_usage_pct"],

            # Minimal demo sxemindən əlavə diaqnostik sahələr — dashboard
            # üçün faydalıdır, başqa istehlakçılar tərəfindən ignore edilə bilər.
            "_meta": {
                "actuator": decision.actuator,
                "notify_farmer": decision.notify_farmer,
                "decision_reason": decision.reason,
                "sub_scores": gpss_result.sub_scores,
                "biomorphic": bio_result.to_dict(),
                "lorawan": fused["lorawan"],
                "edge_ram_usage_mb": resources["edge_ram_usage_mb"],
                "edge_ram_usage_pct": resources["edge_ram_usage_pct"],
                "total_pipeline_latency_ms": round(total_latency_ms, 1),
                "sensor_source": sensor_reading.to_dict(),
            }
        }
