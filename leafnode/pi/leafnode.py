"""
leafnode: look after the Pi and its camera from one command.

    leafnode status              what the Pi and the camera are connected to
    leafnode wifi add            save another Wi-Fi (a phone hotspot) on both
    leafnode wifi list           the networks each one knows
    leafnode wifi remove NAME    forget one on both
    leafnode interval SECONDS    how often the camera takes a photo (10..3600)
    leafnode photo               have the camera take a photo now, and score it
    leafnode update [FILE.bin]   put new firmware on the camera over Wi-Fi

setup.sh installs it as /usr/local/bin/leafnode. From a laptop:

    ssh -t emin@leafnode.local leafnode wifi add

Both devices keep every network they already know, so adding a hotspot at
home changes nothing until the home Wi-Fi is out of range. Passwords are asked
for without echo and never printed or logged.
"""

from __future__ import annotations

import getpass
import os
import subprocess
import sys
from pathlib import Path

import requests

HERE = Path(__file__).resolve().parent
PI = "http://127.0.0.1:" + os.environ.get("LEAFNODE_PORT", "8000")
DEFAULT_FIRMWARE = HERE.parent / "build" / "leafnode.ino.bin"
# Connections this tool creates on the Pi are named like this, so it only ever
# removes its own and never the Wi-Fi the Pi was installed with.
PREFIX = "leafnode-"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    path = HERE / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env[key.strip()] = value.strip()
    return {**env, **{k: v for k, v in os.environ.items() if k.startswith("LEAFNODE_")}}


ENV = load_env()
NODE_KEY = ENV.get("LEAFNODE_NODE_KEY", "")
CAMERA_ID = ENV.get("LEAFNODE_CAMERA_ID", "leafnode-01") or "leafnode-01"
KEY = {"X-Node-Key": NODE_KEY}


def say(text: str = "") -> None:
    print(text, flush=True)


def fail(text: str) -> None:
    print(text, file=sys.stderr, flush=True)
    raise SystemExit(1)


# --- the camera --------------------------------------------------------------


def camera_bases() -> list[str]:
    """Where the camera is: what the Pi service last saw, then its mDNS name."""
    bases = []
    override = ENV.get("LEAFNODE_CAMERA_URL", "").rstrip("/")
    if override:
        bases.append(override)
    try:
        cams = requests.get(f"{PI}/health", timeout=5).json().get("cameras", {})
        host = (cams.get(CAMERA_ID) or {}).get("host")
        if host:
            bases.append(f"http://{host}")
    except (requests.RequestException, ValueError):
        pass
    bases.append(f"http://{CAMERA_ID}.local")
    return list(dict.fromkeys(bases))


def camera(method: str, path: str, **kwargs) -> tuple[requests.Response | None, str]:
    """Calls the camera wherever it answers. Returns (response or None, where)."""
    errors = []
    timeout = kwargs.pop("timeout", (4, 20))
    for base in camera_bases():
        try:
            res = requests.request(method, f"{base}{path}", headers=KEY, timeout=timeout, **kwargs)
            return res, base
        except requests.RequestException as exc:
            if "refused" in str(exc).lower():
                # On the network, but nothing listens: firmware older than 1.2.
                return None, "refused"
            errors.append(f"{base}: {str(exc)[:160]}")
    return None, "; ".join(errors)


def camera_json(method: str, path: str, **kwargs) -> dict | None:
    res, where = camera(method, path, **kwargs)
    if res is None and where == "refused":
        say("  The camera is on, but its firmware is older than 1.2 and has no settings to change.")
        say("  Flash 1.2 once over the serial jumpers: bash ~/leafnode/pi/flash_esp32.sh flash "
            "~/leafnode/build/leafnode.ino.merged.bin")
        return None
    if res is None:
        say(f"  The camera did not answer ({where}). Is it on, and on the same Wi-Fi?")
        return None
    if res.status_code == 404 and path in ("/wifi", "/config", "/hello"):
        say("  The camera's firmware is too old for this. Flash firmware 1.2 once over")
        say("  the serial jumpers (leafnode/pi/flash_esp32.sh); after that, `leafnode update`.")
        return None
    try:
        body = res.json()
    except ValueError:
        body = {"detail": res.text[:200]}
    if res.status_code == 401:
        say("  The camera refused the node key: NODE_KEY in secrets.h is not LEAFNODE_NODE_KEY.")
        return None
    if res.status_code >= 400:
        say(f"  The camera said no: {body.get('detail')}")
        return None
    return body


# --- the Pi's own Wi-Fi (NetworkManager) ---------------------------------------


def nmcli(*args: str, sudo: bool = False, secret: bool = False) -> subprocess.CompletedProcess:
    cmd = (["sudo", "-n"] if sudo else []) + ["nmcli", *args]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0 and not secret:
        say(f"  nmcli: {res.stderr.strip() or res.stdout.strip()}")
    return res


def pi_networks() -> list[tuple[str, str]]:
    """(connection name, SSID) for every Wi-Fi the Pi knows."""
    out = nmcli("-t", "-f", "NAME,TYPE", "connection", "show").stdout
    found = []
    for line in out.splitlines():
        name, _, kind = line.rpartition(":")
        if kind == "802-11-wireless":
            name = name.replace("\\:", ":")
            ssid = nmcli("-g", "802-11-wireless.ssid", "connection", "show", name).stdout.strip()
            found.append((name, ssid))
    return found


def pi_current() -> str:
    for line in nmcli("-t", "-f", "ACTIVE,SSID", "device", "wifi").stdout.splitlines():
        if line.startswith("yes:"):
            return line[4:].replace("\\:", ":")
    return ""


def visible_networks() -> list[tuple[str, int, str]]:
    """What the Pi can hear right now: (SSID, signal, band)."""
    out = nmcli("-t", "-f", "SSID,SIGNAL,FREQ", "device", "wifi", "list", "--rescan", "yes").stdout
    signal_of: dict[str, int] = {}
    has_24: dict[str, bool] = {}
    for line in out.splitlines():
        parts = line.replace("\\:", "\x00").split(":")
        if len(parts) < 3 or not parts[0]:
            continue
        ssid = parts[0].replace("\x00", ":")
        try:
            signal = int(parts[1])
            mhz = int(parts[2].split()[0])
        except ValueError:
            continue
        signal_of[ssid] = max(signal, signal_of.get(ssid, 0))
        # A network that also broadcasts on 2.4 GHz is one the camera can join.
        has_24[ssid] = has_24.get(ssid, False) or mhz < 3000
    return sorted(((s, signal_of[s], "2.4 GHz" if has_24[s] else "5 GHz") for s in signal_of),
                  key=lambda r: -r[1])


# --- commands ------------------------------------------------------------------


def cmd_status() -> None:
    say(f"Pi on Wi-Fi: {pi_current() or 'none'}")
    try:
        h = requests.get(f"{PI}/health", timeout=5).json()
        up = h["upstream"]
        say(f"Pi service:  running, model {h['model'].get('version')}, "
            f"{'server ' + ('reachable' if up['configured'] else 'not set')}, "
            f"{up['queue_depth']} waiting to send")
        cam = h.get("cameras", {}).get(CAMERA_ID, {})
    except (requests.RequestException, ValueError, KeyError):
        say("Pi service:  NOT answering. See: journalctl -u leafnode -n 50")
        cam = {}
    body = camera_json("POST", "/hello")
    if body:
        say(f"Camera:      {body.get('device_id')} at {body.get('ip')}, firmware {body.get('firmware')}, "
            f"on {body.get('ssid')} ({body.get('rssi')} dBm), photo every {body.get('interval_s')} s")
    elif cam:
        say(f"Camera:      last seen at {cam.get('host')}, {cam.get('frame_at') or cam.get('seen_at')}")


def cmd_wifi_list() -> None:
    current = pi_current()
    say("The Pi knows:")
    for name, ssid in pi_networks():
        say(f"  {ssid or name}{'   (connected)' if ssid == current else ''}")
    body = camera_json("GET", "/wifi")
    if body:
        say("The camera knows:")
        say(f"  {body.get('built_in')}   (built in){'   (connected)' if body.get('connected') == body.get('built_in') else ''}")
        for ssid in body.get("saved", []):
            say(f"  {ssid}{'   (connected)' if body.get('connected') == ssid else ''}")


def cmd_wifi_add(name: str | None) -> None:
    if not name:
        say("Looking for Wi-Fi networks... (turn the hotspot on now if you want to pick it)")
        nets = visible_networks()
        for i, (ssid, signal, band) in enumerate(nets[:15], 1):
            warn = "" if band == "2.4 GHz" else "   5 GHz only: the camera cannot use it"
            say(f"  {i:2}. {ssid}  ({signal}%){warn}")
        choice = input("Number from the list, or type the network name exactly: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(nets[:15]):
            name = nets[int(choice) - 1][0]
        else:
            name = choice
    if not name or len(name.encode()) > 32:
        fail("A network name is 1 to 32 characters.")

    password = getpass.getpass(f"Password for {name} (not shown, leave empty for an open network): ")
    if password and not 8 <= len(password) <= 63:
        fail("A WPA2 password is 8 to 63 characters.")
    if password and getpass.getpass("Same password again: ") != password:
        fail("The two did not match. Nothing was saved.")

    # The Pi: a NetworkManager connection beside the existing one. Same
    # priority, so NM stays on whatever it is using and picks this one only
    # when the other is out of range.
    con = PREFIX + "".join(c if c.isalnum() or c in "-_." else "-" for c in name)[:40]
    nmcli("connection", "delete", con, sudo=True, secret=True)
    args = ["connection", "add", "type", "wifi", "ifname", "wlan0", "con-name", con,
            "ssid", name, "connection.autoconnect", "yes"]
    if password:
        args += ["wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password]
    pi_ok = nmcli(*args, sudo=True, secret=True).returncode == 0
    say(f"Pi:     {'saved ' + name if pi_ok else 'could NOT save it (is sudo allowed without a password?)'}")

    body = camera_json("POST", "/wifi", data={"action": "add", "ssid": name, "password": password})
    if body:
        say(f"Camera: saved {name} (it now knows {body.get('built_in')}"
            f"{', ' + ', '.join(body.get('saved', [])) if body.get('saved') else ''})")
    password = ""

    if pi_ok and body:
        say()
        say(f"Done. Both stay on {pi_current() or 'the current Wi-Fi'} for now and move to {name}")
        say("when it is the one in range. Keep the hotspot on 2.4 GHz with WPA2:")
        say('  iPhone: Personal Hotspot > turn on "Maximize Compatibility"')
        say("  Android: Hotspot > AP band 2.4 GHz, security WPA2-Personal")
    else:
        raise SystemExit(1)


def cmd_wifi_remove(name: str) -> None:
    removed = False
    for con, ssid in pi_networks():
        if ssid == name and con.startswith(PREFIX):
            removed = nmcli("connection", "delete", con, sudo=True).returncode == 0
        elif ssid == name:
            say(f"Pi:     {name} was set up when the Pi was installed; leaving it alone.")
    if removed:
        say(f"Pi:     forgot {name}")
    body = camera_json("POST", "/wifi", data={"action": "remove", "ssid": name})
    if body:
        say(f"Camera: forgot {name}")


def cmd_interval(seconds: str) -> None:
    if not seconds.isdigit() or not 10 <= int(seconds) <= 3600:
        fail("Give a number of seconds from 10 to 3600.")
    body = camera_json("POST", "/config", data={"interval_s": seconds})
    if body:
        say(f"The camera now takes a photo every {body.get('interval_s')} s "
            f"(next in {body.get('next_capture_s')} s). It remembers this after a restart.")


def cmd_photo() -> None:
    say("Asking the camera...")
    try:
        res = requests.post(f"{PI}/capture", headers=KEY, timeout=75)
    except requests.RequestException as exc:
        fail(f"The Pi service did not answer: {exc}")
    body = res.json()
    if res.status_code != 200:
        fail(f"No photo: {body.get('detail')} ({body.get('why', '')})")
    if body.get("unreadable"):
        say(f"Photo taken, but it could not be read: {body['unreadable']}")
    else:
        say(f"Photo taken: {body.get('label')} {body.get('confidence')}, risk {body.get('risk_score')} "
            f"({body.get('risk_level')}), {body.get('latency_ms')} ms, "
            f"{'sent to the server' if body.get('queued') else 'kept on the Pi'}")


def cmd_update(path: str | None) -> None:
    firmware = Path(path) if path else DEFAULT_FIRMWARE
    if not firmware.is_file():
        fail(f"No firmware at {firmware}. Build leafnode.ino.bin (not the merged .bin) and copy it there.")
    if firmware.stat().st_size > 1_966_080:
        fail("That file is too big for an app slot; is it the merged .bin? Use leafnode.ino.bin.")
    base = next((b for b in camera_bases() if _answers(b)), None)
    if base is None:
        fail("The camera did not answer. Is it on, and on the same Wi-Fi?")

    say(f"Sending {firmware.name} ({firmware.stat().st_size // 1024} KB) to the camera at {base}...")
    # curl, not requests: the ESP32's upload parser aborts on the way requests
    # streams a large multipart body (every try, 2026-09-25) and takes curl's
    # (every try). The key goes in on stdin, so it is never in the process list.
    for attempt in (1, 2):
        res = subprocess.run(
            ["curl", "-sS", "-m", "180", "-K", "-", "-o", "-", "-w", "\n%{http_code}",
             "-F", f"firmware=@{firmware}", f"{base}/update"],
            input=f'header = "X-Node-Key: {NODE_KEY}"\n', capture_output=True, text=True,
        )
        body, _, code = res.stdout.rpartition("\n")
        if code == "200":
            say("Written. The camera is restarting into it; give it about 15 seconds.")
            return
        if code == "404":
            fail("This camera's firmware cannot update over Wi-Fi yet: flash 1.2 over the serial jumpers once.")
        if code == "401":
            fail("The camera refused the node key: NODE_KEY in secrets.h is not LEAFNODE_NODE_KEY.")
        say(f"  Attempt {attempt} did not take ({code or res.stderr.strip()[:120]}): {body[:120]}")
    fail("The update did not take. The old firmware keeps running; try again closer to the router.")


def _answers(base: str) -> bool:
    try:
        return requests.get(f"{base}/status", timeout=(3, 5)).ok
    except requests.RequestException:
        return False


def main(argv: list[str]) -> None:
    if not NODE_KEY:
        fail(f"LEAFNODE_NODE_KEY is not set in {HERE / '.env'}. Run setup.sh first.")
    args = argv[1:]
    if not args or args[0] in ("-h", "--help", "help"):
        say(__doc__.strip().split("\n\n")[1])
        return
    cmd, rest = args[0], args[1:]
    if cmd == "status":
        cmd_status()
    elif cmd == "wifi" and rest[:1] == ["add"]:
        cmd_wifi_add(" ".join(rest[1:]) or None)
    elif cmd == "wifi" and rest[:1] == ["remove"] and len(rest) > 1:
        cmd_wifi_remove(" ".join(rest[1:]))
    elif cmd == "wifi" and rest[:1] in ([], ["list"]):
        cmd_wifi_list()
    elif cmd == "interval" and len(rest) == 1:
        cmd_interval(rest[0])
    elif cmd == "photo":
        cmd_photo()
    elif cmd == "update":
        cmd_update(rest[0] if rest else None)
    else:
        fail("Unknown command. Try: leafnode help")


if __name__ == "__main__":
    try:
        main(sys.argv)
    except KeyboardInterrupt:
        say()
        raise SystemExit(130)
