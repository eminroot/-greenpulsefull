#!/usr/bin/env bash
# One-time setup on the Raspberry Pi. Run it from anywhere:
#
#     bash ~/leafnode/pi/setup.sh
#
# Safe to run again after editing .env: it keeps what is there, fills in only
# what is missing, and restarts the services so the change takes effect.
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"
DIR="$PWD"
USER_NAME="$(id -un)"

# Files copied over from Windows can arrive with CRLF endings, which turn every
# value in .env into "value\r" and break the token.
sed -i 's/\r$//' ./*.service .env.example requirements.txt
[ -f .env ] && sed -i 's/\r$//' .env

# onnxruntime, which runs the leaf model, publishes Pi wheels for 64-bit only.
# On a 32-bit Raspberry Pi OS pip would fail deep into a source build.
case "$(uname -m)" in
  aarch64|x86_64) ;;
  *) echo "This Pi runs a $(uname -m) (32-bit) OS. Reflash it with the 64-bit"
     echo "Raspberry Pi OS; the leaf model's runtime has no 32-bit build."
     exit 1 ;;
esac

echo "==> system packages"
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv python3-pip curl

echo "==> python environment (first run takes a few minutes)"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install --upgrade --quiet pip
.venv/bin/pip install --quiet -r requirements.txt

echo "==> configuration"
[ -f .env ] || cp .env.example .env
chmod 600 .env
# A .env written before the trained model arrived says LEAFNODE_MODEL=placeholder
# (or the retired ultralytics option). Move it over once. After that
# LEAFNODE_CROP exists, and whatever the file says is kept.
if ! grep -q '^LEAFNODE_CROP=' .env; then
  sed -i -E 's/^LEAFNODE_MODEL=(placeholder|ultralytics)[[:space:]]*$/LEAFNODE_MODEL=greenpulse/' .env
  grep -q '^LEAFNODE_MODEL=' .env || echo 'LEAFNODE_MODEL=greenpulse' >> .env
  echo 'LEAFNODE_CROP=tomato' >> .env
  echo "    model switched to the trained classifier (tomato)."
  echo "    For a pepper greenhouse set LEAFNODE_CROP=pepper in .env and run this again."
fi
if ! grep -qE '^LEAFNODE_NODE_KEY=.+' .env; then
  key="$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')"
  if grep -q '^LEAFNODE_NODE_KEY=' .env; then
    sed -i "s|^LEAFNODE_NODE_KEY=.*|LEAFNODE_NODE_KEY=$key|" .env
  else
    echo "LEAFNODE_NODE_KEY=$key" >> .env
  fi
fi
mkdir -p data/captures weights

echo "==> services"
for unit in leafnode leafnode-agent; do
  sed -e "s|__USER__|$USER_NAME|g" -e "s|__DIR__|$DIR|g" "$unit.service" \
    | sudo tee "/etc/systemd/system/$unit.service" >/dev/null
done
sudo systemctl daemon-reload
sudo systemctl enable --quiet leafnode
sudo systemctl restart leafnode

set -a; . ./.env; set +a
if [ -n "${LEAFNODE_UPSTREAM_URL:-}" ] && [ -n "${LEAFNODE_UPSTREAM_TOKEN:-}" ]; then
  sudo systemctl enable --quiet leafnode-agent
  sudo systemctl restart leafnode-agent
  agent="on"
  if curl -fsS -H "Authorization: Bearer $LEAFNODE_UPSTREAM_TOKEN" \
       "${LEAFNODE_UPSTREAM_URL%/capture}/health" >/dev/null 2>&1; then
    upstream="reachable, token accepted"
  else
    upstream="NOT reachable or token refused. Check the URL and token in .env"
  fi
else
  sudo systemctl disable --now --quiet leafnode-agent 2>/dev/null || true
  agent="off until LEAFNODE_UPSTREAM_URL and LEAFNODE_UPSTREAM_TOKEN are set"
  upstream="not configured, readings stay on the Pi"
fi

# Give uvicorn a moment to bind and the model a moment to load (it loads in
# the background) before asking either anything.
model="no answer"
for _ in $(seq 1 40); do
  model="$(curl -fs http://127.0.0.1:8000/health 2>/dev/null | .venv/bin/python -c '
import json, sys
m = json.load(sys.stdin)["model"]
if m["loaded"]:
    print("%s %s for %s, loaded" % (m["selected"], m["version"], m["crop"]))
elif m["error"]:
    print("NOT loaded: %s. See: journalctl -u leafnode -n 50" % m["error"])
' 2>/dev/null || true)"
  [ -n "$model" ] && break
  sleep 0.5
done

ip="$(hostname -I | awk '{print $1}')"
echo
if curl -fs http://127.0.0.1:8000/health >/dev/null 2>&1; then
  echo "LeafNode service: running on http://$ip:8000"
else
  echo "LeafNode service: NOT answering. See: journalctl -u leafnode -n 50"
fi
echo "Model:            ${model:-still loading, check curl http://127.0.0.1:8000/health}"
echo "Server:           $upstream"
echo "Phone scan agent: $agent"
echo "Clock:            $(timedatectl show -p NTPSynchronized --value 2>/dev/null | sed 's/yes/synchronised/;s/no/NOT synchronised yet/')"
cat <<EOF

Put these in the ESP32 firmware before flashing:
  config.h    #define PI_HOST   "$ip"
  secrets.h   #define NODE_KEY  "$LEAFNODE_NODE_KEY"

Logs:  journalctl -u leafnode -f      journalctl -u leafnode-agent -f
EOF
