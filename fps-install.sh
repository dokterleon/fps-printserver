#!/bin/bash
set -e

echo "╔══════════════════════════════════════╗"
echo "║  FPS Flitshokje Print Server Setup  ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── 1. SYSTEEM UPDATE ──
echo "📦 Systeem updaten..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
  cups cups-client cups-common cups-filters printer-driver-gutenprint \
  avahi-daemon avahi-utils \
  hostapd dnsmasq \
  python3 python3-pip python3-flask python3-requests \
  python3-qrcode python3-pil python3-venv \
  git imagemagick \
  2>/dev/null

echo "✅ Systeem pakketten geïnstalleerd"

# ── 2. PYTHON PAKKETTEN ──
echo "🐍 Python pakketten installeren..."
sudo pip3 install --break-system-packages \
  pyarmor qrcode requests flask \
  2>/dev/null

echo "✅ Python pakketten geïnstalleerd"

# ── 3. FPS SOFTWARE ──
echo "📥 FPS software downloaden..."
cd /home/flitshokje
if [ -d "flitshokje-printserver" ]; then
  cd flitshokje-printserver
  git pull
else
  git clone https://github.com/dokterleon/fps-printserver.git flitshokje-printserver
  cd flitshokje-printserver
fi
mkdir -p logs

echo "✅ FPS software gedownload"

# ── 4. CUPS CONFIGURATIE ──
echo "🖨  CUPS configureren..."
sudo usermod -a -G lpadmin flitshokje
sudo usermod -a -G lp flitshokje
sudo sed -i 's/Browsing Off/Browsing On/' /etc/cups/cupsd.conf 2>/dev/null || true
sudo sed -i 's/Listen localhost:631/Listen 0.0.0.0:631/' /etc/cups/cupsd.conf 2>/dev/null || true
sudo systemctl enable cups
sudo systemctl restart cups

echo "✅ CUPS geconfigureerd"

# ── 5. AVAHI / AIRPRINT ──
echo "📡 AirPrint configureren..."
sudo systemctl enable avahi-daemon
sudo systemctl restart avahi-daemon

echo "✅ AirPrint geconfigureerd"

# ── 6. WIFI HOTSPOT ──
echo "📶 WiFi hotspot configureren..."
sudo systemctl unmask hostapd 2>/dev/null || true
sudo systemctl enable hostapd 2>/dev/null || true

echo "✅ WiFi hotspot geconfigureerd"

# ── 7. SYSTEMD SERVICE ──
echo "⚙️  FPS service installeren..."
sudo tee /etc/systemd/system/flitshokje-printserver.service > /dev/null << 'SVCEOF'
[Unit]
Description=FPS Flitshokje Print Server
After=network.target cups.service avahi-daemon.service

[Service]
Type=simple
User=root
WorkingDirectory=/home/flitshokje/flitshokje-printserver
ExecStart=/usr/bin/python3 app.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

sudo systemctl daemon-reload
sudo systemctl enable flitshokje-printserver

echo "✅ FPS service geïnstalleerd"

# ── 8. SERIENUMMER INSTELLEN ──
echo ""
echo "╔══════════════════════════════════════╗"
echo "║         Unit configuratie            ║"
echo "╚══════════════════════════════════════╝"
echo "Serienummer invoeren:"
read -p "FPS-2026-" serial </dev/tty
serial="FPS-2026-$serial"

if [ -z "$serial" ] || [ "$serial" = "FPS-2026-" ]; then
  echo "❌ Serienummer verplicht!"
  exit 1
fi

echo "🔍 Controleren of $serial al bestaat..."
response=$(curl -s "https://central.flitshokje.nl/api/status/$serial")
if echo "$response" | grep -q '"client_id"'; then
  echo "⚠️  $serial bestaat al!"
  read -p "Toch doorgaan? (j/n): " confirm </dev/tty
  if [ "$confirm" != "j" ]; then
    echo "❌ Geannuleerd."
    exit 1
  fi
fi

echo "{\"client_id\":\"$serial\",\"name\":\"\",\"location\":\"\"}" > /home/flitshokje/flitshokje-printserver/logs/beacon.json

# ── 9. STARTEN ──
echo ""
echo "🚀 FPS Print Server starten..."
sudo systemctl start flitshokje-printserver
sleep 3

echo ""
echo "╔══════════════════════════════════════╗"
echo "║  ✅ Installatie compleet!            ║"
echo "║  📟 Serienummer: $serial"
echo "║  🌐 Dashboard: http://$(hostname -I | awk '{print $1}')"
echo "╚══════════════════════════════════════╝"

# Script verwijdert zichzelf
# Script verwijderd
