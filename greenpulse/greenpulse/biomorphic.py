"""
Layer 3: Biomorphic Feature Extraction
----------------------------------------------------------------
Hesabatda qeyd olunan "Layer 2 və Layer 4 Təkrarlanması" problemini həll
edir: köhnə demoda eyni zədə-piksel-faizi düsturu iki fərqli qatda təkrar
yazılmışdı. Burada bu, TƏK bir HSV-based rəng analizi modulunda
birləşdirilir. Yalnız yarpaq maskası DAXİLİNDƏ hesablayır:
    - saralma faizi (chlorosis proxy -> su/qida stresi)
    - qəhvəyi-ləkə faizi (toxuma zədəsi proxy)
    - ümumi damage_percentage (demo JSON sxemində birbaşa istifadə olunur)
"""

import numpy as np
import cv2


# Yarpaq görüntüləri üçün ayarlanmış HSV diapazonları (OpenCV: H 0-179, S/V 0-255)
YELLOW_HSV_LOW = np.array([18, 60, 60])
YELLOW_HSV_HIGH = np.array([34, 255, 255])

BROWN_HSV_LOW = np.array([0, 40, 20])
BROWN_HSV_HIGH = np.array([20, 255, 170])

HEALTHY_GREEN_LOW = np.array([35, 40, 40])
HEALTHY_GREEN_HIGH = np.array([85, 255, 255])


class BiomorphicResult:
    def __init__(self, yellow_pct, brown_pct, healthy_pct, damage_percentage):
        self.yellow_pct = yellow_pct
        self.brown_pct = brown_pct
        self.healthy_pct = healthy_pct
        self.damage_percentage = damage_percentage

    def to_dict(self):
        return {
            "yellow_pct": round(self.yellow_pct, 2),
            "brown_pct": round(self.brown_pct, 2),
            "healthy_pct": round(self.healthy_pct, 2),
            "damage_percentage": round(self.damage_percentage, 2),
        }


def analyze(image_bgr: np.ndarray, leaf_mask: np.ndarray, damage_mask: np.ndarray = None) -> BiomorphicResult:
    """
    image_bgr:   orijinal BGR şəkil, maskalarla eyni H,W ölçüsündə
    leaf_mask:   binary (H,W) uint8, 1 = yarpaq pikseli (Layer 2-dən)
    damage_mask: opsional binary (H,W) uint8 — model ayrıca "damage" class-ı
                 versə istifadə olunur; vermirsə None ötürün, funksiya
                 zədəni təmamilə HSV rəng həddindən hesablayacaq.
    """
    leaf_pixel_count = int(leaf_mask.sum())
    if leaf_pixel_count == 0:
        # Yarpaq aşkarlanmayıb — sıfıra bölmə əvəzinə boş nəticə qaytarırıq.
        return BiomorphicResult(0.0, 0.0, 0.0, 0.0)

    hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)

    yellow_mask = cv2.inRange(hsv, YELLOW_HSV_LOW, YELLOW_HSV_HIGH)
    brown_mask = cv2.inRange(hsv, BROWN_HSV_LOW, BROWN_HSV_HIGH)
    green_mask = cv2.inRange(hsv, HEALTHY_GREEN_LOW, HEALTHY_GREEN_HIGH)

    leaf_bool = leaf_mask.astype(bool)
    yellow_in_leaf = (yellow_mask > 0) & leaf_bool
    brown_in_leaf = (brown_mask > 0) & leaf_bool
    green_in_leaf = (green_mask > 0) & leaf_bool

    yellow_pct = 100.0 * yellow_in_leaf.sum() / leaf_pixel_count
    brown_pct = 100.0 * brown_in_leaf.sum() / leaf_pixel_count
    healthy_pct = 100.0 * green_in_leaf.sum() / leaf_pixel_count

    if damage_mask is not None and damage_mask.sum() > 0:
        # Model birbaşa damage mask veribsə, onu əsas götürürük (daha
        # dəqiqdir), yellow/brown isə əlavə diaqnostik siqnal kimi qalır.
        damage_in_leaf = (damage_mask.astype(bool)) & leaf_bool
        damage_percentage = 100.0 * damage_in_leaf.sum() / leaf_pixel_count
    else:
        # Yalnız rəngdən hesabla: sağlam-yaşıl olmayan və sarı/qəhvəyi
        # olan hər piksel zədəli toxuma sayılır.
        damage_percentage = min(100.0, yellow_pct + brown_pct)

    return BiomorphicResult(yellow_pct, brown_pct, healthy_pct, damage_percentage)
