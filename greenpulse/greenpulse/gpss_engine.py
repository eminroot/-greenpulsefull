"""
Layer 5: GPSS Engine (Global Plant Stress Score)
----------------------------------------------------------------
Aşağıdakıları birləşdirərək TƏK bir 0-100 "bitki stress skoru" hesablayır:
    - vision-dan gələn damage_percentage (Layer 2+3)   -> çəki 0.40
    - su stresi, soil_moisture-dan törəmə                -> çəki 0.30
    - termal stress, temperature-dan törəmə               -> çəki 0.15
    - işıq stresi, light-dan törəmə                         -> çəki 0.15

Bu, hesabatın "Layer 5: GPSS Engine — riyazi düstur əsasında 0-100 arası
ümumi stress skorunun real zamanlı hesablanması" vədini yerinə yetirir.
Çəkilər və ideal diapazonlar aşağıda tənzimlənə bilən sabitlərdir — real
sera datası toplandıqdan sonra kalibrasiya edilməlidir.
"""

from dataclasses import dataclass


# Tipik istixana bitkisi üçün ideal/rahat diapazonlar (bitki növünə görə tənzimlənməlidir)
IDEAL_SOIL_MOISTURE = (45, 70)     # %
IDEAL_TEMPERATURE = (18, 28)       # °C
IDEAL_HUMIDITY = (50, 75)          # %
IDEAL_LIGHT = (400, 800)           # lux

WEIGHT_DAMAGE = 0.40
WEIGHT_WATER = 0.30
WEIGHT_THERMAL = 0.15
WEIGHT_LIGHT = 0.15


@dataclass
class GPSSResult:
    gpss_score: int
    risk_level: str
    stress_type: str
    sub_scores: dict


def _deviation_score(value: float, low: float, high: float, hard_low: float, hard_high: float) -> float:
    """
    Dəyərin ideal [low, high] diapazonuna nisbətən 0-100 stress töhfəsini
    qaytarır. 0 = tam diapazon daxilində. Fizioloji hədd dəyərlərinə
    (hard_low/hard_high) yaxınlaşdıqca 100-ə doğru artır.
    """
    if low <= value <= high:
        return 0.0
    if value < low:
        span = max(low - hard_low, 1e-6)
        return max(0.0, min(100.0, 100.0 * (low - value) / span))
    span = max(hard_high - high, 1e-6)
    return max(0.0, min(100.0, 100.0 * (value - high) / span))


def compute(damage_percentage: float, soil_moisture: float, temperature: float,
            humidity: float, light: float) -> GPSSResult:

    water_score = _deviation_score(soil_moisture, *IDEAL_SOIL_MOISTURE, hard_low=0, hard_high=100)
    thermal_score = _deviation_score(temperature, *IDEAL_TEMPERATURE, hard_low=-5, hard_high=45)
    light_score = _deviation_score(light, *IDEAL_LIGHT, hard_low=0, hard_high=1500)
    damage_score = max(0.0, min(100.0, damage_percentage))

    raw_score = (
        WEIGHT_DAMAGE * damage_score +
        WEIGHT_WATER * water_score +
        WEIGHT_THERMAL * thermal_score +
        WEIGHT_LIGHT * light_score
    )
    gpss_score = int(round(max(0.0, min(100.0, raw_score))))

    if gpss_score <= 25:
        risk_level = "Low"
    elif gpss_score <= 50:
        risk_level = "Medium"
    elif gpss_score <= 75:
        risk_level = "High"
    else:
        risk_level = "Critical"

    sub_scores = {
        "damage_score": round(damage_score, 1),
        "water_score": round(water_score, 1),
        "thermal_score": round(thermal_score, 1),
        "light_score": round(light_score, 1),
    }

    weight_map = {
        "damage_score": WEIGHT_DAMAGE, "water_score": WEIGHT_WATER,
        "thermal_score": WEIGHT_THERMAL, "light_score": WEIGHT_LIGHT,
    }
    # Çəkilənmiş ən böyük töhfəni verən amil "stress_type" etiketini müəyyən edir.
    dominant = max(sub_scores, key=lambda k: sub_scores[k] * weight_map[k])

    stress_type_map = {
        "damage_score": "Tissue Damage",
        "water_score": "Water Stress",
        "thermal_score": "Heat Stress",
        "light_score": "Light Stress",
    }
    stress_type = "Healthy" if gpss_score <= 15 else stress_type_map[dominant]

    return GPSSResult(gpss_score, risk_level, stress_type, sub_scores)
