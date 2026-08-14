#!/bin/bash
clear
echo "================================"
echo "  FPS Flitshokje Print Server"
echo "  Unit Setup"
echo "================================"
echo ""
read -p "Serienummer: FPS-2026-" serial
serial="FPS-2026-$serial"

if [ -z "$serial" ]; then
    echo "❌ Serienummer is verplicht!"
    exit 1
fi

echo "{\"client_id\":\"$serial\",\"name\":\"\",\"location\":\"\"}" > ~/flitshokje-printserver/logs/beacon.json

sudo systemctl restart flitshokje-printserver

echo ""
echo "================================"
echo "✅ Unit $serial klaar!"
echo "📡 Beacon verstuurd naar central.flitshokje.nl"
echo "🔑 Licentie check bij volgende herstart"
echo "================================"
echo ""
rm -- "$0"
echo "🗑  Setup script verwijderd"
