"""
CLI Demo — Streamlit olmadan tez test üçün
----------------------------------------------------------------
İstifadə:
    python run_cli_demo.py path/to/leaf.jpg
    python run_cli_demo.py path/to/leaf.jpg --weights models/yolo11n-seg.pt --scenario drought

Streamlit-i işə salmazdan əvvəl YOLOv11n-Seg çəkilərinin və pipeline-ın
düzgün işlədiyini doğrulamaq üçün istifadə edin.
"""

import argparse
import json
import sys

import cv2

from pipeline import GreenPulsePipeline


def main():
    parser = argparse.ArgumentParser(description="GreenPulse pipeline-ı CLI-dan işə sal")
    parser.add_argument("image_path", help="Yarpaq şəklinin yolu")
    parser.add_argument("--weights", default="models/yolo11n-seg.pt", help="YOLOv11n-Seg .pt faylının yolu")
    parser.add_argument("--device", default="cpu", help="cpu və ya cuda:0")
    parser.add_argument("--scenario", default="normal",
                         choices=["normal", "drought", "heat", "low_light"],
                         help="Simulyasiya ediləcək sensor ssenarisi")
    args = parser.parse_args()

    image = cv2.imread(args.image_path)
    if image is None:
        print(f"XƏTA: şəkil oxuna bilmədi: {args.image_path}", file=sys.stderr)
        sys.exit(1)

    print(f"YOLOv11n-Seg yüklənir: {args.weights} ...")
    pipeline = GreenPulsePipeline(weights_path=args.weights, device=args.device)

    print(f"Pipeline işə salınır (ssenari: {args.scenario}) ...")
    result = pipeline.run(image, sensor_mode="simulated", scenario=args.scenario)

    print("\n=== GreenPulse Pipeline Nəticəsi ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
