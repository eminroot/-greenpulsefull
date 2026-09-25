"""
Layer 4: Digital Twin Sensor Fusion
----------------------------------------------------------------
HAL-dan (Layer 1) gələn raw SensorReading-i real LoRaWAN şəbəkəsində
ötürüləcəyi kimi paketləyir: kompakt byte payload + bu protokolun gətirdiyi
realistik gecikmə (latency/airtime). Bu, hesabatda qeyd olunan boşluqdur:
"LoRaWAN Gecikmə Simulyasiyasının Olmaması" — köhnə demoda protokolun real
paket strukturu və gecikməsi heç simulyasiya edilmirdi.
"""

import struct
import random
from dataclasses import dataclass

from hal import SensorReading


# EU868 / SF7 / 125kHz üçün təxmini LoRaWAN airtime modeli (~6 baytlıq payload).
# Real airtime spreading factor, bandwidth, coding rate və payload ölçüsündən
# asılıdır — bu sabitlər tipik qısa SF7 uplink-i təxmin edir.
LORAWAN_BASE_AIRTIME_MS = 41.0       # preamble/overhead
LORAWAN_PER_BYTE_MS = 1.5            # hər əlavə payload baytı üçün
LORAWAN_NETWORK_JITTER_MS = (5, 60)  # gateway + backend gecikmə dəyişkənliyi


@dataclass
class LoRaWANPacket:
    payload_hex: str
    payload_bytes: int
    airtime_ms: float
    network_latency_ms: float
    total_latency_ms: float
    rssi_dbm: float
    snr_db: float


def encode_payload(reading: SensorReading) -> bytes:
    """
    Sensor dəyərlərini kompakt binary LoRaWAN-tipli payload-a bağlayır:
        soil_moisture : uint8   (0-100 %)
        temperature   : int16   (°C * 10, işarəli)
        humidity      : uint8   (0-100 %)
        light         : uint16  (lux, max 65535)
    Cəmi: 6 bayt — real, məhdud LoRaWAN uplink-i üçün realistikdir.
    """
    soil = max(0, min(255, int(round(reading.soil_moisture))))
    temp = max(-3276, min(3276, int(round(reading.temperature * 10))))
    hum = max(0, min(255, int(round(reading.humidity))))
    light = max(0, min(65535, int(round(reading.light))))
    return struct.pack(">BhBH", soil, temp, hum, light)


def decode_payload(payload: bytes) -> dict:
    soil, temp, hum, light = struct.unpack(">BhBH", payload)
    return {
        "soil_moisture": soil,
        "temperature": temp / 10.0,
        "humidity": hum,
        "light": light,
    }


def simulate_uplink(reading: SensorReading) -> LoRaWANPacket:
    """
    Bir oxumanı LoRaWAN üzərindən göndərməyi simulyasiya edir və real
    deployment-də olacaq end-to-end gecikməni qaytarır.
    """
    payload = encode_payload(reading)
    n_bytes = len(payload)

    airtime_ms = LORAWAN_BASE_AIRTIME_MS + n_bytes * LORAWAN_PER_BYTE_MS
    network_latency_ms = random.uniform(*LORAWAN_NETWORK_JITTER_MS)
    total_latency_ms = airtime_ms + network_latency_ms

    # Simulyasiya edilmiş radio link keyfiyyəti (dashboard üçün kosmetik,
    # amma kənd ərazisindəki sera deployment-i üçün məntiqli diapazonlar).
    rssi_dbm = round(random.uniform(-120, -70), 1)
    snr_db = round(random.uniform(-15, 10), 1)

    return LoRaWANPacket(
        payload_hex=payload.hex(),
        payload_bytes=n_bytes,
        airtime_ms=round(airtime_ms, 2),
        network_latency_ms=round(network_latency_ms, 2),
        total_latency_ms=round(total_latency_ms, 2),
        rssi_dbm=rssi_dbm,
        snr_db=snr_db,
    )


def fuse(reading: SensorReading) -> dict:
    """
    Layer 4-ün public giriş nöqtəsi: raw sensor oxumasını alır, LoRaWAN
    ötürülməsini simulyasiya edir və nəticəni pipeline-ın qalan hissəsinə
    (GPSS Engine) ötürür.
    """
    packet = simulate_uplink(reading)
    return {
        "sensors": reading.to_dict(),
        "lorawan": {
            "payload_hex": packet.payload_hex,
            "payload_bytes": packet.payload_bytes,
            "airtime_ms": packet.airtime_ms,
            "network_latency_ms": packet.network_latency_ms,
            "total_latency_ms": packet.total_latency_ms,
            "rssi_dbm": packet.rssi_dbm,
            "snr_db": packet.snr_db,
        },
    }
