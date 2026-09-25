"""
GreenPulse - Simulator surucusu  (Layer 38 / 39)

Mevcut `src/actuator_simulator.py` dosyasini SARMALAR. O dosyanin tek
bir satiri degismedi: davranis, surum numarasi ve sema dogrulamasi
aynen korunur.

Bu sarmalayici yalnizca iki sey yapar:

  1. Simulatorun `SIMULATED_*` durumlarini normallestirilmis
     `AckState` degerlerine esler
  2. Ham yaniti `raw` alaninda oldugu gibi tasir - denetim izi kaybolmaz

Fiziksel eyleme HER ZAMAN False'tur. Simulator semasi bunu zaten
`physical_actuation: const false` ile kilitler; burada da ayrica
sabitlenir ki, ileride biri yanlislikla degistirmesin.
"""
from __future__ import annotations

from src.actuator_simulator import SIMULATOR_VERSION, simulate_actuator
from src.hardware_driver import AckState, ActuatorResult

#: Simulator durumu -> normallestirilmis durum
_STATE_MAP = {
    "SIMULATED_EXECUTED": AckState.EXECUTED,
    "SIMULATED_REJECTED": AckState.REJECTED,
    "SIMULATED_FAILED": AckState.FAILED,
    "SIMULATED_TIMEOUT": AckState.TIMEOUT,
}


class SimulatorDriver:
    """Yazilim simulatoru. GPIO, pompa veya ag baglantisi YOKTUR."""

    name = "sim"
    physical = False

    def __init__(self, scenario: str = "SUCCESS") -> None:
        self.scenario = scenario

    def send(self, command: dict, *, scenario: str | None = None,
             **_: object) -> ActuatorResult:
        raw = simulate_actuator(command, scenario or self.scenario)
        state = _STATE_MAP.get(raw.get("status"))
        if state is None:
            # Simulator semasi disinda bir durum dondurduyse bunu
            # BASARI saymayiz; bilinmeyen durum REJECTED'dir.
            state = AckState.REJECTED
        return ActuatorResult(
            state=state,
            command_id=raw.get("command_id"),
            driver=self.name,
            physical_actuation=False,
            error_code=raw.get("error_code"),
            timestamp=raw.get("timestamp"),
            raw=raw,
        )

    def health(self) -> dict:
        return {
            "driver": self.name,
            "ready": True,
            "physical_actuation": False,
            "simulator_version": SIMULATOR_VERSION,
            "note": ("Yazilim simulatoru - gercek donanim baglanmadi. "
                     "Uretilen ACK kayitlari fiziksel eyleme KANITI "
                     "DEGILDIR."),
        }
