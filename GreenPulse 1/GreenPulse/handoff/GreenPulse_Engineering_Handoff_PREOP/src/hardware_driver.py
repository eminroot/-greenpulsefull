"""
GreenPulse - Aktuator surucu arayuzu  (Layer 38 / 39)

NEDEN BU DOSYA VAR
------------------
Simulator daha once koda BAGLIYDI: `actuator_audit.py` dogrudan
`from src.actuator_simulator import simulate_actuator` yapiyordu. Gercek
role baglanacagi gun bu, kaynak kodu duzenlemeyi gerektirirdi - sunum
gunu yapilabilecek en riskli is.

Bu modul aradaki sozlesmeyi tanimlar. Mevcut hicbir dosya degismedi:
simulator oldugu gibi duruyor, yalnizca bir SARMALAYICI arkasina alindi.

IKI AYRI SOZLESME VAR - BIRLESTIRILMEDI
---------------------------------------
    configs/ack_error_schema_v1.json      YALNIZCA SIMULASYON
        status : SIMULATED_EXECUTED / _REJECTED / _FAILED / _TIMEOUT
        simulated          : const true
        physical_actuation : const false
        real_hardware_ack  : null

    release/schemas/ack_error_schema_v1.json   GERCEK DONANIM
        status : ACK / FAIL / TIMEOUT

Birincisi kasten kilitlidir: o semadan gecen bir yanit "fiziksel eyleme
oldu" DIYEMEZ. Bu bir guvenlik karari oldugu icin gevsetilmedi.

Cozum: her iki dunya da kendi semasinda kalir; bu modul ortak bir
NORMALLESTIRILMIS sonuc tipi dondurur. Boru hatti hangi surucunun bagli
oldugunu bilmek zorunda kalmaz.

SECIM
-----
    GREENPULSE_HARDWARE=sim     (varsayilan) - simulator
    GREENPULSE_HARDWARE=relay   gercek GPIO/role
    GREENPULSE_HARDWARE=none    aktuator yok, yalnizca gozlem

Varsayilan DAIMA `sim`. Ortam degiskeni tanimsizsa hicbir fiziksel
eyleme olusmaz - guvenli tarafa duser.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol, runtime_checkable

DRIVER_ENV = "GREENPULSE_HARDWARE"
DEFAULT_DRIVER = "sim"


class AckState(str, Enum):
    """
    Normallestirilmis ACK durumu - her iki sozlesmenin ortak dili.

    Surucuye ozgu degerler (`SIMULATED_EXECUTED`, `ACK` ...) bu dort
    duruma esleyerek gelir; boru hatti yalnizca bunlari gorur.
    """

    EXECUTED = "EXECUTED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"

    @property
    def starts_cooldown(self) -> bool:
        """
        Yalnizca GERCEKTEN calisan bir eylem bekleme suresi baslatir.

        REJECTED/FAILED/TIMEOUT sonrasi cooldown baslatmak, pompa hic
        calismadigi halde bitkiyi bekletmek demektir.
        """
        return self is AckState.EXECUTED


@dataclass(frozen=True)
class ActuatorResult:
    """Surucuden donen normallestirilmis sonuc."""

    state: AckState
    command_id: str | None
    driver: str
    physical_actuation: bool
    error_code: str | None = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())
    #: Surucunun kendi ham yaniti - denetim icin oldugu gibi saklanir.
    raw: dict | None = None

    @property
    def ok(self) -> bool:
        return self.state is AckState.EXECUTED


@runtime_checkable
class ActuatorDriver(Protocol):
    """
    Bir aktuator surucusunun karsilamasi gereken sozlesme.

    Gercek donanim yazan kisi YALNIZCA bunu uygulamak zorundadir.
    Boru hattinda, API'de veya testlerde hicbir degisiklik gerekmez.
    """

    name: str
    physical: bool

    def send(self, command: dict, **kwargs) -> ActuatorResult:
        """Komutu gonderir ve normallestirilmis sonucu dondurur."""
        ...

    def health(self) -> dict:
        """Surucunun kullanima hazir olup olmadigini bildirir."""
        ...


class NullDriver:
    """Aktuator yok: sistem yalnizca gozlem yapar, eylem uretmez."""

    name = "none"
    physical = False

    def send(self, command: dict, **kwargs) -> ActuatorResult:
        return ActuatorResult(
            state=AckState.REJECTED,
            command_id=command.get("command_id") if isinstance(command, dict) else None,
            driver=self.name,
            physical_actuation=False,
            error_code="NO_ACTUATOR_CONFIGURED",
        )

    def health(self) -> dict:
        return {
            "driver": self.name,
            "ready": True,
            "physical_actuation": False,
            "note": "Aktuator yapilandirilmadi; eylem uretilmez.",
        }


def available_drivers() -> dict[str, str]:
    return {
        "sim": "Yazilim simulatoru - fiziksel eyleme YOK (varsayilan)",
        "relay": "Gercek GPIO/role surucusu - yalnizca Raspberry Pi",
        "none": "Aktuator yok, yalnizca gozlem",
    }


def build_driver(kind: str | None = None) -> ActuatorDriver:
    """
    Surucuyu ortam degiskeninden secer.

    `kind` acikca verilirse ortam degiskeni yok sayilir - testler bu
    sayede ortama bagimli kalmaz.
    """
    name = (kind or os.environ.get(DRIVER_ENV, DEFAULT_DRIVER)).strip().lower()

    if name in ("", "sim", "simulator", "simulation"):
        from src.hardware_driver_simulator import SimulatorDriver
        return SimulatorDriver()

    if name in ("relay", "gpio", "real"):
        from src.hardware_driver_relay import RelayDriver
        return RelayDriver()

    if name in ("none", "off", "disabled"):
        return NullDriver()

    raise ValueError(
        f"Bilinmeyen {DRIVER_ENV} degeri: {name!r}. "
        f"Gecerli: {', '.join(available_drivers())}"
    )
