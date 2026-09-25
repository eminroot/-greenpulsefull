"""
Layer 1: Unified Ingestion & Hardware Abstraction Layer (HAL)
----------------------------------------------------------------
Məqsəd:
    Pipeline-ın qalan hissəsinə sensor + görüntü datasını oxumaq üçün
    TƏK bir interfeys təqdim edir — fərq etməz data haradan gəlir:
        - JSON-based simulyator (semifinal demo üçün)
        - real ESP32 + DHT22 sensor node (gələcək hardware inteqrasiyası)
        - manual override (münsif dashboard-da slider-ləri dəyişir)

    Bu, optimizasiya hesabatında qeyd olunan boşluqdur: orijinal demo
    özünü "hardware-agnostic" elan etsə də, real bunu təmin edən heç bir
    abstraksiya təbəqəsi yox idi. Bu modul həmin təbəqədir.

    Prinsip: ESP32 qoşulanda YALNIZ bu fayldakı ESP32SensorSource sinfi
    dəyişir — pipeline-ın qalan 6 qatından heç biri toxunulmur.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
import random
import time


@dataclass
class SensorReading:
    soil_moisture: float   # faiz, 0-100
    temperature: float     # Selsi
    humidity: float        # faiz, 0-100
    light: float            # lux
    timestamp: float = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self):
        return asdict(self)


class SensorSource(ABC):
    """Hər sensor backend-i bunu implement etməlidir."""

    @abstractmethod
    def read(self) -> SensorReading:
        ...

    @property
    @abstractmethod
    def source_type(self) -> str:
        ...


class SimulatedSensorSource(SensorSource):
    """
    Canlı demo üçün rəqəmsal əkiz (digital twin) sensor generatoru.
    Demo zamanı müəyyən bir stress ssenarisinə uyğun realistik dəyərlər
    yaradır ki, münsiflərə fərqli stress tipləri göstərilə bilsin.
    """

    SCENARIOS = {
        "normal":    dict(soil_moisture=(55, 70), temperature=(20, 26), humidity=(55, 70), light=(450, 700)),
        "drought":   dict(soil_moisture=(10, 28), temperature=(28, 36), humidity=(30, 45), light=(600, 900)),
        "heat":      dict(soil_moisture=(35, 55), temperature=(33, 40), humidity=(25, 40), light=(700, 950)),
        "low_light": dict(soil_moisture=(40, 60), temperature=(18, 24), humidity=(60, 80), light=(50, 180)),
    }

    def __init__(self, scenario: str = "normal"):
        if scenario not in self.SCENARIOS:
            raise ValueError(f"Naməlum ssenari '{scenario}'. Seçimlər: {list(self.SCENARIOS)}")
        self.scenario = scenario

    def set_scenario(self, scenario: str):
        if scenario not in self.SCENARIOS:
            raise ValueError(f"Naməlum ssenari '{scenario}'. Seçimlər: {list(self.SCENARIOS)}")
        self.scenario = scenario

    def read(self) -> SensorReading:
        r = self.SCENARIOS[self.scenario]
        return SensorReading(
            soil_moisture=round(random.uniform(*r["soil_moisture"]), 1),
            temperature=round(random.uniform(*r["temperature"]), 1),
            humidity=round(random.uniform(*r["humidity"]), 1),
            light=round(random.uniform(*r["light"]), 1),
        )

    @property
    def source_type(self) -> str:
        return f"simulated:{self.scenario}"


class ManualOverrideSensorSource(SensorSource):
    """
    Streamlit dashboard-dakı slider-lərdən gələn dəyərləri pipeline-a
    ötürür. Digər bütün source-larla eyni interfeysə malikdir, ona görə
    pipeline-ın qalan hissəsi fərqi bilməz.
    """

    def __init__(self, soil_moisture=50.0, temperature=24.0, humidity=60.0, light=500.0):
        self._values = dict(soil_moisture=soil_moisture, temperature=temperature,
                             humidity=humidity, light=light)

    def update(self, **kwargs):
        self._values.update({k: v for k, v in kwargs.items() if k in self._values})

    def read(self) -> SensorReading:
        return SensorReading(**self._values)

    @property
    def source_type(self) -> str:
        return "manual_override"


class ESP32SensorSource(SensorSource):
    """
    Real hardware inteqrasiyası üçün STUB (demo sonrası roadmap addımı).
    ESP32-dən seriya port üzərindən DHT22 + torpaq nəmlik sensoru
    dəyərlərini oxuyur. Semifinal üçün ZƏRURI deyil, amma HAL
    müqaviləsini doğru saxlayır: simulyasiyadan real hardware-ə keçid
    YALNIZ bu sinfi yazmaqla olur.

    Gözlənilən ESP32 firmware sətri formatı (seriya port üzərindən CSV):
        "<soil_moisture>,<temperature>,<humidity>,<light>\\n"
    """

    def __init__(self, connection: str = "/dev/ttyUSB0", baud: int = 115200):
        self.connection = connection
        self.baud = baud
        self._serial = None  # lazy-load — real qoşulma yalnız read() çağırılanda olur

    def _ensure_connected(self):
        if self._serial is None:
            try:
                import serial  # pyserial — opsional asılılıq
                self._serial = serial.Serial(self.connection, self.baud, timeout=2)
            except ImportError as e:
                raise RuntimeError(
                    "ESP32SensorSource üçün pyserial lazımdır. Quraşdırın: pip install pyserial"
                ) from e

    def read(self) -> SensorReading:
        self._ensure_connected()
        line = self._serial.readline().decode("utf-8").strip()
        soil, temp, hum, light = (float(x) for x in line.split(","))
        return SensorReading(soil_moisture=soil, temperature=temp, humidity=hum, light=light)

    @property
    def source_type(self) -> str:
        return f"esp32:{self.connection}"


def get_sensor_source(mode: str = "simulated", **kwargs) -> SensorSource:
    """
    Factory funksiya — Layer 1-in pipeline üçün TƏK giriş nöqtəsi.
    Çağıran kod heç vaxt konkret sinifi birbaşa yaratmır.
    """
    if mode == "simulated":
        return SimulatedSensorSource(scenario=kwargs.get("scenario", "normal"))
    if mode == "manual":
        return ManualOverrideSensorSource(**kwargs)
    if mode == "esp32":
        return ESP32SensorSource(**kwargs)
    raise ValueError(f"Naməlum sensor mode: {mode}")
