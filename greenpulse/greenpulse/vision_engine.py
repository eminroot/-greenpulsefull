"""
Layer 2: Leaf Vision AI Engine
----------------------------------------------------------------
YOLOv11n-Seg modelini (yolo11n-seg.pt) sarmalayır. Yalnız bunlara
cavabdehdir:
    - yarpaq şəklində seqmentasiya inference-i işə salmaq
    - yarpaq maskasını və (varsa) zədə alt-maskasını çıxarmaq
    - raw detection datasını + vaxt ölçmələrini qaytarmaq

Rəng analizi (HSV) BURADA YOXDUR — bu, Layer 3-ün (Biomorphic Feature
Extraction) işidir. Köhnə demo-da bu iki funksiya (detection + rəng analizi)
iki fərqli qatda təkrarlanırdı (hesabatdakı "Layer 2 və Layer 4
Təkrarlanması" problemi). Burada hər qat YALNIZ bir işi görür.
"""

import time
import numpy as np
import cv2

try:
    from ultralytics import YOLO
except ImportError:
    YOLO = None  # ultralytics quraşdırılmasa belə fayl import oluna bilsin
                 # — xəta yalnız real istifadə zamanı (predict çağırılanda) atılır.


class VisionResult:
    def __init__(self, leaf_mask, damage_mask, confidence, raw_boxes, inference_ms):
        self.leaf_mask = leaf_mask          # binary mask (H, W) uint8, 1 = yarpaq pikseli
        self.damage_mask = damage_mask      # binary mask (H, W) uint8, 1 = zədəli piksel
        self.confidence = confidence        # float 0-1, ən yaxşı detection confidence
        self.raw_boxes = raw_boxes          # list of dicts: class, conf, xyxy
        self.inference_ms = inference_ms    # float, model forward-pass gecikməsi (ms)


class LeafVisionEngine:
    """
    yolo11n-seg.pt çəkilərinin train edildiyi data.yaml-da gözlənilən
    class id-lər:
        0: leaf
        1: damage   (chlorosis / necrosis / lesion — dataset-ə uyğun)

    Əgər sizin data.yaml-da fərqli sıralamadır, aşağıdakı
    LEAF_CLASS_ID / DAMAGE_CLASS_ID dəyərlərini ona uyğun dəyişin.

    QEYD: Əgər modeliniz YALNIZ "leaf" class-ı ilə train olunubsa (tək
    class), damage_mask boş qalacaq və Layer 3 zədəni HSV rəng analizi
    ilə avtomatik hesablayacaq (bax: biomorphic.py) — sistem hər iki
    halda da işləyir.
    """

    LEAF_CLASS_ID = 0
    DAMAGE_CLASS_ID = 1

    def __init__(self, weights_path: str = "models/yolo11n-seg.pt", device: str = "cpu", conf: float = 0.25):
        if YOLO is None:
            raise ImportError("ultralytics quraşdırılmayıb. Çalışdırın: pip install ultralytics")
        self.model = YOLO(weights_path)
        self.device = device
        self.conf = conf

    def predict(self, image: np.ndarray) -> VisionResult:
        """
        image: BGR numpy array (cv2.imread / cv2.VideoCapture formatında)
        """
        h, w = image.shape[:2]
        t0 = time.perf_counter()
        results = self.model.predict(
            source=image, conf=self.conf, device=self.device, verbose=False
        )
        inference_ms = (time.perf_counter() - t0) * 1000.0

        leaf_mask = np.zeros((h, w), dtype=np.uint8)
        damage_mask = np.zeros((h, w), dtype=np.uint8)
        raw_boxes = []
        best_conf = 0.0

        result = results[0]
        if result.masks is not None:
            masks_data = result.masks.data.cpu().numpy()       # (N, mh, mw)
            classes = result.boxes.cls.cpu().numpy().astype(int)
            confs = result.boxes.conf.cpu().numpy()
            xyxy = result.boxes.xyxy.cpu().numpy()

            for i in range(len(classes)):
                mask_i = cv2.resize(masks_data[i], (w, h), interpolation=cv2.INTER_NEAREST)
                mask_i = (mask_i > 0.5).astype(np.uint8)

                cls_id = int(classes[i])
                conf_i = float(confs[i])
                raw_boxes.append({
                    "class_id": cls_id,
                    "confidence": conf_i,
                    "xyxy": xyxy[i].tolist(),
                })
                best_conf = max(best_conf, conf_i)

                if cls_id == self.LEAF_CLASS_ID:
                    leaf_mask = np.maximum(leaf_mask, mask_i)
                elif cls_id == self.DAMAGE_CLASS_ID:
                    damage_mask = np.maximum(damage_mask, mask_i)

        return VisionResult(leaf_mask, damage_mask, best_conf, raw_boxes, inference_ms)
