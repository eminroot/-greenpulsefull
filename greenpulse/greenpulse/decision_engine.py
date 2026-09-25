"""
Layer 6: Autonomous Decision Engine
----------------------------------------------------------------
GPSS skorunu + stress_type-ı avtonom aktuator qərarına çevirir. Sistemin
həqiqətən "proaktiv" olmasını təmin edən hissə budur: hesabatın vəd etdiyi
kimi, zədə görünməzdən ƏVVƏL, eşik dəyər keçilməzdən qabaq hərəkətə keçir.
"""

from dataclasses import dataclass


ACTION_THRESHOLD = 50   # bu GPSS dəyərindən yuxarıda avtonom hərəkət başlayır
ALERT_THRESHOLD = 76    # bu dəyərdən yuxarıda fermerə də bildiriş göndərilir


@dataclass
class Decision:
    decision: str
    actuator: str
    notify_farmer: bool
    reason: str


def decide(gpss_score: int, stress_type: str) -> Decision:
    if gpss_score < ACTION_THRESHOLD:
        return Decision(
            decision="MONITORING",
            actuator="NONE",
            notify_farmer=False,
            reason=f"GPSS={gpss_score} hərəkət həddindən ({ACTION_THRESHOLD}) aşağıdır; bitki sağlam diapazondadır.",
        )

    notify = gpss_score >= ALERT_THRESHOLD

    if stress_type == "Water Stress":
        return Decision("IRRIGATION_ON", "WATER_PUMP", notify,
                         f"Torpaq nəmlik defisiti aşkarlandı (GPSS={gpss_score}).")
    if stress_type == "Heat Stress":
        return Decision("VENTILATION_ON", "FAN", notify,
                         f"Temperatur stresi aşkarlandı (GPSS={gpss_score}).")
    if stress_type == "Light Stress":
        return Decision("SUPPLEMENTAL_LIGHT_ON", "GROW_LIGHT", notify,
                         f"İşıq çatışmazlığı aşkarlandı (GPSS={gpss_score}).")
    if stress_type == "Tissue Damage":
        return Decision("ALERT_AGRONOMIST", "NONE", True,
                         f"Görünən toxuma zədəsi aşkarlandı (GPSS={gpss_score}); insan müayinəsi tələb olunur.")

    return Decision("MONITORING", "NONE", notify, f"Yüksək GPSS={gpss_score}, dominant tək səbəb yoxdur.")
