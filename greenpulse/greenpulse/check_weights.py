"""
Mövcud çəki faylının artıq fine-tune olunub-olunmadığını yoxlayır.
----------------------------------------------------------------
COCO-pretrained yolo11n-seg.pt "person", "car", "dog" kimi 80 ümumi class
tanıyır — leaf/damage YOXDUR. Bu skript class adlarını çap edib sizə deyir
ki, modeliniz artıq leaf-üçün train olunub, yoxsa hələ default COCO
modelidir.

İstifadə:
    python check_weights.py models/yolo11n-seg.pt
"""

import sys
from ultralytics import YOLO

COCO_SIGNATURE_CLASSES = {"person", "car", "dog", "cat", "bicycle", "bus", "truck"}


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "models/yolo11n-seg.pt"
    model = YOLO(path)

    print(f"Çəki faylı: {path}")
    print(f"Class sayı: {len(model.names)}")
    print(f"Class adları: {dict(model.names)}")

    present_coco = set(model.names.values()) & COCO_SIGNATURE_CLASSES
    if present_coco:
        print("\n⚠️  DİQQƏT: Bu, default COCO-pretrained model kimi görünür")
        print(f"    (aşkarlanan COCO class-ları: {present_coco}).")
        print("    Bu model hələ yarpaq/zədə aşkarlaya bilməz.")
        print("    Növbəti addım: öz dataset-inizlə train.py vasitəsilə fine-tune edin.")
    else:
        print("\n✅ Bu, custom (fine-tuned) model kimi görünür.")
        print("    Yuxarıdakı class adlarının 'leaf' / 'damage' (və ya oxşar) olduğunu yoxlayın")
        print("    və lazım gəlsə vision_engine.py-dakı LEAF_CLASS_ID/DAMAGE_CLASS_ID-i uyğunlaşdırın.")


if __name__ == "__main__":
    main()
