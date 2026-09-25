"""
GreenPulse — YOLOv11n-Seg Fine-Tuning Skripti
----------------------------------------------------------------
COCO üzərində pretrained olan yolo11n-seg.pt-ni sizin öz yarpaq
(+ opsional zədə) seqmentasiya dataset-inizlə fine-tune edir.

İSTİFADƏ:
    1) Roboflow (və ya başqa mənbədən) "YOLOv11 Instance Segmentation"
       formatında dataset endirin. Struktur belə olmalıdır:

           dataset/
             data.yaml
             train/images, train/labels
             valid/images, valid/labels
             test/images,  test/labels      (opsional)

    2) Skripti işə salın:
       python train.py --data dataset/data.yaml --epochs 80

    3) Nəticə çəkiləri: runs/segment/train/weights/best.pt
       Bunu köçürün:
       cp runs/segment/train/weights/best.pt models/yolo11n-seg.pt
"""

import argparse
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser(description="YOLOv11n-Seg-i öz leaf dataset-inizlə fine-tune edin")
    parser.add_argument("--data", required=True, help="data.yaml faylının yolu (Roboflow export formatı)")
    parser.add_argument("--base-weights", default="yolo11n-seg.pt",
                         help="Başlanğıc çəkilər (COCO-pretrained, ultralytics ilk dəfə avtomatik endirir)")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=16)
    parser.add_argument("--device", default="cpu", help="cpu, 0, və ya 0,1 (çoxlu GPU)")
    parser.add_argument("--patience", type=int, default=20, help="Early stopping səbri (epoch sayı)")
    args = parser.parse_args()

    model = YOLO(args.base_weights)

    model.train(
        data=args.data,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        patience=args.patience,
        project="runs/segment",
        name="train",
        # Sera daxili işıqlandırma dəyişkənliyinə qarşı yüngül augmentasiya:
        hsv_h=0.015, hsv_s=0.6, hsv_v=0.4,
        degrees=10, translate=0.1, scale=0.3,
        fliplr=0.5, flipud=0.0,
    )

    metrics = model.val()
    print("\n=== Validasiya Metrikləri ===")
    print(metrics)

    print("\n✅ Ən yaxşı çəkilər: runs/segment/train/weights/best.pt")
    print("   Köçürün: cp runs/segment/train/weights/best.pt models/yolo11n-seg.pt")


if __name__ == "__main__":
    main()
