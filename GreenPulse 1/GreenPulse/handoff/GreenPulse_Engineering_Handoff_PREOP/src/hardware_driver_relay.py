"""
GreenPulse - Gercek role / MOSFET surucusu  (Layer 38 / 39)

DONANIM MUHENDISI ICIN
----------------------
Doldurmaniz gereken tek yer `_drive_pin()` govdesidir. Geri kalan her
sey - dogrulama, zaman asimi, guvenlik kilitleri, ACK uretimi - hazir.

Bu dosya Windows'ta da SORUNSUZ import edilir: GPIO kutuphanesi modul
yuklenirken DEGIL, yalnizca gercekten pompa surulecegi an import edilir.
Bu sayede testler ve gelistirme makinesi etkilenmez.

GUVENLIK VARSAYILANI: REDDET
----------------------------
Yapilandirma eksikse surucu pompayi CALISTIRMAZ; acik hata koduyla
reddeder. "Belki calisir" diye denemek, sera ortaminda pompayi acik
birakma riski tasir.

Calismasi icin UC sart birden gereklidir:

    GREENPULSE_RELAY_ENABLE=1        acik onay (arming)
    GREENPULSE_RELAY_PIN=<BCM no>    hangi pin
    GREENPULSE_RELAY_MAX_SECONDS=<s> ust sinir (varsayilan 60)

Ucunden biri eksikse sonuc: REJECTED / RELAY_NOT_ARMED.

SURE SINIRI
-----------
Istenen sure `MAX_SECONDS` degerini asarsa komut REDDEDILIR - sessizce
kirpilmaz. Sessiz kirpma, "30 saniye suladim" diyen bir kayitla
gercekte 5 saniye calisan bir pompa arasinda fark birakmaz.

ACK SOZLESMESI
--------------
Gercek donanim `release/schemas/ack_error_schema_v1.json` sozlesmesini
kullanir (ACK / FAIL / TIMEOUT). Simulator semasi (`configs/...`)
BILEREK simulasyona kilitlidir ve buradan KULLANILMAZ.
"""
from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from src.hardware_driver import AckState, ActuatorResult

ENV_ENABLE = "GREENPULSE_RELAY_ENABLE"
ENV_PIN = "GREENPULSE_RELAY_PIN"
ENV_ACTIVE_HIGH = "GREENPULSE_RELAY_ACTIVE_HIGH"
ENV_MAX_SECONDS = "GREENPULSE_RELAY_MAX_SECONDS"

DEFAULT_MAX_SECONDS = 60.0


def _env_int(name: str) -> int | None:
    raw = os.environ.get(name, "").strip()
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name, "").strip()
    try:
        value = float(raw)
        return value if value > 0 else default
    except (TypeError, ValueError):
        return default


class RelayDriver:
    """
    Gercek GPIO/role surucusu. YALNIZCA Raspberry Pi uzerinde calisir.

    Pompa surme mantigi `_drive_pin()` icindedir ve su an BILEREK
    bostur - gercek donanim baglanmadan once doldurulmamalidir.
    """

    name = "relay"
    physical = True

    #: `_drive_pin()` doldurulduktan SONRA True yapin.
    #:
    #: Bu bayrak `health()` ciktisini dogru tutar: bayrak False iken
    #: sistem kendini "hazir" ILAN ETMEZ. Otomatik tespit etmeye
    #: calismak yerine acik bir onay istiyoruz - donanim surucusunun
    #: gercekten yazildigini yalnizca onu yazan kisi bilir.
    IMPLEMENTED = False

    def __init__(self) -> None:
        self.pin = _env_int(ENV_PIN)
        self.active_high = os.environ.get(ENV_ACTIVE_HIGH, "1").strip() != "0"
        self.max_seconds = _env_float(ENV_MAX_SECONDS, DEFAULT_MAX_SECONDS)
        self.armed = os.environ.get(ENV_ENABLE, "").strip() == "1"

    # -- guvenlik kontrolleri ---------------------------------------------

    def _blocked_reason(self, duration: float) -> str | None:
        if not self.armed:
            return "RELAY_NOT_ARMED"
        if self.pin is None:
            return "RELAY_PIN_NOT_CONFIGURED"
        if duration <= 0:
            return "INVALID_DURATION"
        if duration > self.max_seconds:
            # Sessizce kirpilmaz - kayit ile gercek arasinda fark kalmasin.
            return "DURATION_EXCEEDS_LIMIT"
        return None

    # -- doldurulacak tek yer ---------------------------------------------

    def _drive_pin(self, duration_s: float) -> None:
        """
        Pompayi `duration_s` saniye calistirir.

        DONANIM MUHENDISI: govdeyi burada doldurun. Ornek (gpiozero):

            from gpiozero import OutputDevice
            relay = OutputDevice(self.pin, active_high=self.active_high,
                                 initial_value=False)
            try:
                relay.on()
                time.sleep(duration_s)
            finally:
                relay.off()          # <- `finally` SART

        `finally` olmadan bir istisna pompayi ACIK BIRAKIR. Kutuphaneyi
        modul basinda degil, BURADA import edin; aksi halde dosya
        Windows'ta import edilemez ve testler kirilir.
        """
        raise NotImplementedError(
            "Role surme mantigi henuz yazilmadi. `_drive_pin()` govdesini "
            "doldurun. Gercek donanim baglanana kadar bu surucu bilerek "
            "calismaz."
        )

    # -- surucu sozlesmesi -------------------------------------------------

    def send(self, command: dict, *, duration_s: float | None = None,
             **_: object) -> ActuatorResult:
        cid = command.get("command_id") if isinstance(command, dict) else None
        duration = float(
            duration_s
            if duration_s is not None
            else (command.get("duration_s") if isinstance(command, dict) else 0)
            or 0
        )

        blocked = self._blocked_reason(duration)
        if blocked:
            return self._result(AckState.REJECTED, cid, blocked,
                                physical=False, duration=duration)

        started = time.monotonic()
        try:
            self._drive_pin(duration)
        except NotImplementedError:
            return self._result(AckState.REJECTED, cid,
                                "RELAY_DRIVER_NOT_IMPLEMENTED",
                                physical=False, duration=duration)
        except TimeoutError:
            return self._result(AckState.TIMEOUT, cid, "RELAY_TIMEOUT",
                                physical=True, duration=duration)
        except Exception as exc:                            # noqa: BLE001
            # Donanim hatasi sessizce yutulmaz: FAILED doner, ust katman
            # guvenli duruma gecer ve eylemi geri alir.
            return self._result(AckState.FAILED, cid,
                                f"RELAY_ERROR:{type(exc).__name__}",
                                physical=True, duration=duration)

        return self._result(AckState.EXECUTED, cid, None, physical=True,
                            duration=duration,
                            elapsed=round(time.monotonic() - started, 3))

    def _result(self, state: AckState, cid, error, *, physical: bool,
                duration: float, elapsed: float | None = None
                ) -> ActuatorResult:
        # `release/schemas/ack_error_schema_v1.json` dilinde ham kayit.
        raw = {
            "status": {AckState.EXECUTED: "ACK",
                       AckState.FAILED: "FAIL",
                       AckState.TIMEOUT: "TIMEOUT"}.get(state, "FAIL"),
            "command_id": cid,
            "error_code": error,
            "requested_duration_s": duration,
            "elapsed_s": elapsed,
            "pin": self.pin,
            "armed": self.armed,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        return ActuatorResult(
            state=state, command_id=cid, driver=self.name,
            physical_actuation=physical, error_code=error, raw=raw,
        )

    def health(self) -> dict:
        reason = self._blocked_reason(1.0)
        implemented = self.IMPLEMENTED
        if not implemented and reason is None:
            reason = "RELAY_DRIVER_NOT_IMPLEMENTED"
        return {
            "driver": self.name,
            "ready": reason is None and implemented,
            "armed": self.armed,
            "pin": self.pin,
            "active_high": self.active_high,
            "max_seconds": self.max_seconds,
            "physical_actuation": True,
            "blocked_reason": reason or ("RELAY_DRIVER_NOT_IMPLEMENTED"
                                         if not implemented else None),
            "note": ("Gercek donanim surucusu. Yapilandirma eksikse veya "
                     "`_drive_pin()` doldurulmamissa pompa CALISMAZ."),
        }
