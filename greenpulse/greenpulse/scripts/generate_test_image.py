"""
Sintetik test şəkli generatoru
----------------------------------------------------------------
Real yarpaq şəkliniz yoxdursa, pipeline-ı (xüsusən Layer 3 — HSV analizi)
test etmək üçün sadə, yaşıl-oval + qəhvəyi-ləkəli "yarpaq-bənzəri" şəkil
yaradır. YOLO modeli bunu real yarpaq kimi aşkar etməyə bilər (sintetikdir),
amma Layer 3-4-5-6-i ayrıca test etmək üçün faydalıdır.

İstifadə:
    python scripts/generate_test_image.py --out test_leaf.jpg --damage 25
"""

import argparse
import numpy as np
import cv2


def generate(width=640, height=480, damage_pct=15) -> np.ndarray:
    img = np.full((height, width, 3), (40, 40, 40), dtype=np.uint8)  # tünd fon

    # Yaşıl oval "yarpaq"
    center = (width // 2, height // 2)
    axes = (width // 3, height // 3)
    cv2.ellipse(img, center, axes, 0, 0, 360, (40, 160, 60), -1)  # BGR yaşıl

    # damage_pct-ə uyğun təsadüfi qəhvəyi ləkələr əlavə et
    rng = np.random.default_rng(42)
    leaf_area = np.pi * axes[0] * axes[1]
    target_damage_area = leaf_area * (damage_pct / 100.0)
    drawn_area = 0.0
    while drawn_area < target_damage_area:
        r = int(rng.uniform(5, 25))
        angle = rng.uniform(0, 2 * np.pi)
        dist = rng.uniform(0, min(axes) * 0.8)
        cx = int(center[0] + dist * np.cos(angle))
        cy = int(center[1] + dist * np.sin(angle))
        cv2.circle(img, (cx, cy), r, (20, 70, 120), -1)  # BGR qəhvəyi
        drawn_area += np.pi * r * r

    return img


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="test_leaf.jpg")
    parser.add_argument("--damage", type=float, default=15.0, help="Təxmini zədə faizi")
    args = parser.parse_args()

    img = generate(damage_pct=args.damage)
    cv2.imwrite(args.out, img)
    print(f"Sintetik test şəkli yaradıldı: {args.out} (hədəf zədə: ~{args.damage}%)")
