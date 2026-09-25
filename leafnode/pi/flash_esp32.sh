#!/usr/bin/env bash
# Flash the ESP32-CAM through the Pi's own serial pins. No USB-TTL adapter.
#
# Two wires on top of the 5V/GND the breadboard already carries:
#   Pi pin 8   (GPIO14, TX)  ->  ESP32-CAM U0R
#   Pi pin 10  (GPIO15, RX)  ->  ESP32-CAM U0T
# Both boards already share GND through the rail, which serial needs.
#
#   bash flash_esp32.sh setup                  one time, then reboot
#   bash flash_esp32.sh flash leafnode.bin     GPIO0 jumpered to GND, RST pressed
#   bash flash_esp32.sh monitor [seconds]      read the node's serial log
#
# The two serial wires can stay connected afterwards: the node's log then
# arrives on the Pi, which is the easiest way to debug it from a laptop.
set -euo pipefail
cd "$(dirname "$(readlink -f "$0")")"

MODEL="$(tr -d '\0' < /proc/device-tree/model 2>/dev/null || echo unknown)"
CONFIG=/boot/firmware/config.txt
[ -f "$CONFIG" ] || CONFIG=/boot/config.txt

# On a Pi 5, serial0 is the separate debug connector, and GPIO14/15 is UART0.
if [[ "$MODEL" == *"Raspberry Pi 5"* ]]; then
  PORT="${ESP_PORT:-/dev/ttyAMA0}"
else
  PORT="${ESP_PORT:-/dev/serial0}"
fi
# The ROM always answers at 115200; esptool then moves the data to ESP_BAUD.
# 460800 writes the 4 MB image in ~25 s instead of ~70 s, which matters: an
# ESP32-CAM on breadboard power can brown out partway through a long write.
BAUD="${ESP_BAUD:-460800}"

need_esptool() {
  if [ ! -x .venv/bin/esptool ]; then
    echo "==> installing esptool into the LeafNode venv"
    [ -d .venv ] || python3 -m venv .venv
    .venv/bin/pip install --quiet "esptool>=5"
  fi
}

cmd="${1:-}"
case "$cmd" in
  setup)
    echo "==> $MODEL"
    # Take the login console off the serial pins, turn the UART on.
    sudo raspi-config nonint do_serial_cons 1
    sudo raspi-config nonint do_serial_hw 0
    if [[ "$MODEL" == *"Raspberry Pi 5"* ]] && ! grep -q '^dtparam=uart0=on' "$CONFIG"; then
      echo "dtparam=uart0=on" | sudo tee -a "$CONFIG" >/dev/null
    fi
    sudo usermod -aG dialout "$(id -un)"
    need_esptool
    echo
    echo "Serial pins handed over. Reboot once:  sudo reboot"
    echo "After that the port is $PORT"
    ;;

  flash)
    image="${2:?usage: flash_esp32.sh flash <file.merged.bin>}"
    [ -e "$PORT" ] || { echo "$PORT does not exist. Run: bash flash_esp32.sh setup, then reboot."; exit 1; }
    need_esptool
    # Only one program can hold the port, so close any running monitor first.
    echo "==> checking the ESP32 is in download mode on $PORT"
    # --no-stub at 115200: the probe must leave the ROM exactly as it found it.
    # A flasher stub left running at a faster baud would not answer the write.
    if ! .venv/bin/esptool --chip esp32 --port "$PORT" --baud 115200 --no-stub \
         --before no-reset --after no-reset chip-id >/dev/null 2>&1; then
      cat <<EOF

The ESP32 did not answer. Put it in download mode:
  1. jumper ESP32-CAM GPIO0 to GND (Pi pin 9 is a GND)
  2. press RST; on a breadboard the button faces down, so instead pull the
     ESP32's 5V wire for two seconds and push it back
  3. run this command again
If it still fails, check the serial wires: Pi pin 8 to U0R, Pi pin 10 to U0T.
EOF
      exit 1
    fi
    echo "==> writing $image at $BAUD baud (~25 s at 460800); do not touch the wires"
    .venv/bin/esptool --chip esp32 --port "$PORT" --baud "$BAUD" \
      --before no-reset --after no-reset write-flash 0x0 "$image"
    cat <<EOF

Flashed and verified. Now:
  1. take GPIO0 off GND (left on, the board boots into download mode again)
  2. press RST, or pull the ESP32's 5V wire for two seconds
  3. bash flash_esp32.sh monitor 40     to watch it boot and send its first frame
EOF
    ;;

  monitor)
    seconds="${2:-30}"
    [ -e "$PORT" ] || { echo "$PORT does not exist. Run setup first."; exit 1; }
    need_esptool   # brings pyserial with it
    echo "==> $PORT at 115200 for ${seconds}s (Ctrl+C to stop)"
    .venv/bin/python - "$PORT" "$seconds" <<'EOF'
import sys, time, serial
port, seconds = sys.argv[1], float(sys.argv[2])
with serial.Serial(port, 115200, timeout=0.5) as s:
    end = time.time() + seconds
    while time.time() < end:
        line = s.readline()
        if line:
            print(line.decode("utf-8", "replace").rstrip(), flush=True)
EOF
    ;;

  *)
    sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'
    exit 1
    ;;
esac
