"""
Aktuator surucu arayuzu testleri  (Layer 38 / 39)

NEDEN BU TESTLER VAR
--------------------
Simulator daha once koda BAGLIYDI; gercek role baglanacagi gun kaynak
kodu duzenlemek gerekiyordu. Arayuz bu bagi kopardi. Bu dosya iki seyi
ayni anda korur:

  1. Yeni arayuzun guvenlik varsayilanlari (yapilandirma eksikse REDDET)
  2. ESKI DAVRANISIN DEGISMEDIGI - simulator sarmalandi, degistirilmedi

Ikincisi daha onemli: bir soyutlama eklerken mevcut davranisi sessizce
kaydirmak, en pahali regresyon turudur.
"""
from __future__ import annotations

import uuid

import pytest

from src.actuator_simulator import simulate_actuator
from src.hardware_driver import (
    DRIVER_ENV, AckState, ActuatorDriver, ActuatorResult, NullDriver,
    available_drivers, build_driver,
)
from src.hardware_driver_relay import (
    ENV_ENABLE, ENV_MAX_SECONDS, ENV_PIN, RelayDriver,
)
from src.hardware_driver_simulator import SimulatorDriver


def valid_command() -> dict:
    """Simulatorun kabul ettigi tam gecerli komut."""
    return {
        "command_id": str(uuid.uuid4()),
        "observation_id": str(uuid.uuid4()),
        "plant_id": "P01",
        "mode": "SIMULATION_ONLY",
        "test_only": True,
        "origin": "TEST_HARNESS",
        "action": "IRRIGATION_TEST",
        "target": "MAIN_IRRIGATION_PUMP",
    }


# ---------------------------------------------------------------------------
# Surucu secimi
# ---------------------------------------------------------------------------


class TestDriverSelection:
    def test_default_is_simulator(self, monkeypatch):
        """
        Ortam degiskeni YOKSA simulator secilir.

        Bu, guvenlik acisindan en onemli varsayilan: yapilandirilmamis
        bir sistem asla fiziksel eyleme uretmez.
        """
        monkeypatch.delenv(DRIVER_ENV, raising=False)
        d = build_driver()
        assert d.name == "sim"
        assert d.physical is False

    @pytest.mark.parametrize("value,expected", [
        ("sim", "sim"), ("SIM", "sim"), ("simulator", "sim"),
        ("relay", "relay"), ("GPIO", "relay"), ("real", "relay"),
        ("none", "none"), ("off", "none"), ("disabled", "none"),
    ])
    def test_env_selects_driver(self, monkeypatch, value, expected):
        monkeypatch.setenv(DRIVER_ENV, value)
        assert build_driver().name == expected

    def test_explicit_argument_overrides_env(self, monkeypatch):
        """Testler ortama bagimli kalmamali."""
        monkeypatch.setenv(DRIVER_ENV, "relay")
        assert build_driver("sim").name == "sim"

    def test_unknown_value_raises(self, monkeypatch):
        """Yanlis yazim SESSIZCE simulatore dusmemeli."""
        monkeypatch.setenv(DRIVER_ENV, "rely")
        with pytest.raises(ValueError, match="Bilinmeyen"):
            build_driver()

    def test_all_drivers_satisfy_protocol(self):
        for kind in available_drivers():
            assert isinstance(build_driver(kind), ActuatorDriver)

    def test_every_driver_reports_health(self):
        for kind in available_drivers():
            h = build_driver(kind).health()
            assert {"driver", "ready", "physical_actuation"} <= set(h)


# ---------------------------------------------------------------------------
# Simulator sarmalayicisi - eski davranis korunuyor mu?
# ---------------------------------------------------------------------------


class TestSimulatorWrapper:
    @pytest.mark.parametrize("scenario,expected", [
        ("SUCCESS", AckState.EXECUTED),
        ("FAILURE", AckState.FAILED),
        ("TIMEOUT", AckState.TIMEOUT),
        ("UNKNOWN_SCENARIO", AckState.REJECTED),
    ])
    def test_status_mapping(self, scenario, expected):
        r = SimulatorDriver().send(valid_command(), scenario=scenario)
        assert r.state is expected

    def test_invalid_command_is_rejected(self):
        r = SimulatorDriver().send({"command_id": "not-a-uuid"})
        assert r.state is AckState.REJECTED
        assert r.error_code == "COMMAND_NOT_AUTHORIZED"

    def test_raw_response_is_preserved(self):
        """Denetim izi kaybolmamali - ham yanit oldugu gibi tasinir."""
        cmd = valid_command()
        r = SimulatorDriver().send(cmd)
        assert r.raw is not None
        assert r.raw["simulated"] is True
        assert r.raw["physical_actuation"] is False
        assert r.raw["real_hardware_ack"] is None

    def test_wrapper_matches_underlying_simulator(self):
        """
        REGRESYON: sarmalayici, dogrudan cagrilan simulatorle AYNI
        sonucu vermeli. Soyutlama davranisi kaydirmamali.
        """
        cmd = valid_command()
        direct = simulate_actuator(cmd, "SUCCESS")
        wrapped = SimulatorDriver().send(cmd, scenario="SUCCESS")
        assert wrapped.raw["status"] == direct["status"]
        assert wrapped.raw["error_code"] == direct["error_code"]
        assert wrapped.raw["plant_id"] == direct["plant_id"]
        assert wrapped.raw["target"] == direct["target"]

    def test_simulator_never_claims_physical_actuation(self):
        for scenario in ("SUCCESS", "FAILURE", "TIMEOUT"):
            r = SimulatorDriver().send(valid_command(), scenario=scenario)
            assert r.physical_actuation is False


# ---------------------------------------------------------------------------
# Role surucusu - guvenlik varsayilani REDDET
# ---------------------------------------------------------------------------


class TestRelaySafetyDefaults:
    def _clean(self, monkeypatch):
        for e in (ENV_ENABLE, ENV_PIN, ENV_MAX_SECONDS):
            monkeypatch.delenv(e, raising=False)

    def test_refuses_when_not_armed(self, monkeypatch):
        """
        Acik onay (arming) olmadan pompa CALISMAZ.

        "Belki calisir" diye denemek, sera ortaminda pompayi acik
        birakma riski tasir.
        """
        self._clean(monkeypatch)
        monkeypatch.setenv(ENV_PIN, "17")
        r = RelayDriver().send(valid_command(), duration_s=5)
        assert r.state is AckState.REJECTED
        assert r.error_code == "RELAY_NOT_ARMED"
        assert r.physical_actuation is False

    def test_refuses_without_pin(self, monkeypatch):
        self._clean(monkeypatch)
        monkeypatch.setenv(ENV_ENABLE, "1")
        r = RelayDriver().send(valid_command(), duration_s=5)
        assert r.state is AckState.REJECTED
        assert r.error_code == "RELAY_PIN_NOT_CONFIGURED"

    def test_duration_over_limit_is_rejected_not_clipped(self, monkeypatch):
        """
        Sure sinirini asan komut REDDEDILIR, sessizce KIRPILMAZ.

        Sessiz kirpma, "30 saniye suladim" diyen kayitla gercekte 5
        saniye calisan pompa arasinda fark birakmaz.
        """
        self._clean(monkeypatch)
        monkeypatch.setenv(ENV_ENABLE, "1")
        monkeypatch.setenv(ENV_PIN, "17")
        monkeypatch.setenv(ENV_MAX_SECONDS, "10")
        r = RelayDriver().send(valid_command(), duration_s=30)
        assert r.state is AckState.REJECTED
        assert r.error_code == "DURATION_EXCEEDS_LIMIT"
        assert r.raw["requested_duration_s"] == 30

    @pytest.mark.parametrize("bad", [0, -5])
    def test_invalid_duration_rejected(self, monkeypatch, bad):
        self._clean(monkeypatch)
        monkeypatch.setenv(ENV_ENABLE, "1")
        monkeypatch.setenv(ENV_PIN, "17")
        r = RelayDriver().send(valid_command(), duration_s=bad)
        assert r.state is AckState.REJECTED
        assert r.error_code == "INVALID_DURATION"

    def test_unimplemented_driver_refuses(self, monkeypatch):
        """
        `_drive_pin()` doldurulmadan pompa calismaz - ve bu durum
        ACIK bir hata koduyla bildirilir.
        """
        self._clean(monkeypatch)
        monkeypatch.setenv(ENV_ENABLE, "1")
        monkeypatch.setenv(ENV_PIN, "17")
        r = RelayDriver().send(valid_command(), duration_s=5)
        assert r.state is AckState.REJECTED
        assert r.error_code == "RELAY_DRIVER_NOT_IMPLEMENTED"
        assert r.physical_actuation is False

    def test_health_does_not_claim_ready(self, monkeypatch):
        """Sistem kendini yanlislikla 'hazir' ilan etmemeli."""
        self._clean(monkeypatch)
        monkeypatch.setenv(ENV_ENABLE, "1")
        monkeypatch.setenv(ENV_PIN, "17")
        h = RelayDriver().health()
        assert h["ready"] is False
        assert h["blocked_reason"] == "RELAY_DRIVER_NOT_IMPLEMENTED"

    def test_import_works_without_gpio_library(self):
        """
        GPIO kutuphanesi modul basinda import EDILMEMELI; aksi halde
        Windows'ta dosya import edilemez ve tum test kumesi kirilir.
        """
        import src.hardware_driver_relay as m
        src = __import__("pathlib").Path(m.__file__).read_text(encoding="utf-8")
        head = src[:src.index("class RelayDriver")]
        for lib in ("RPi.GPIO", "gpiozero", "lgpio", "pigpio"):
            assert f"import {lib}" not in head


# ---------------------------------------------------------------------------
# Null surucu ve cooldown kurali
# ---------------------------------------------------------------------------


class TestNullDriverAndCooldown:
    def test_null_driver_never_acts(self):
        r = NullDriver().send(valid_command())
        assert r.state is AckState.REJECTED
        assert r.error_code == "NO_ACTUATOR_CONFIGURED"
        assert r.physical_actuation is False

    @pytest.mark.parametrize("state,expected", [
        (AckState.EXECUTED, True), (AckState.REJECTED, False),
        (AckState.FAILED, False), (AckState.TIMEOUT, False),
    ])
    def test_only_executed_starts_cooldown(self, state, expected):
        """
        Pompa calismadiysa bekleme suresi BASLAMAZ.

        Aksi halde bitki, hic sulanmadigi halde cooldown boyunca
        bloke kalir.
        """
        assert state.starts_cooldown is expected

    def test_result_ok_matches_executed(self):
        r = ActuatorResult(state=AckState.EXECUTED, command_id="x",
                           driver="sim", physical_actuation=False)
        assert r.ok is True
        assert ActuatorResult(state=AckState.FAILED, command_id="x",
                              driver="sim", physical_actuation=False).ok is False
