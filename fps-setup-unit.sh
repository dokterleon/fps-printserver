#!/bin/bash
clear
echo "================================"
echo "  FPS Flitshokje Print Server"
echo "  Unit Setup"
echo "================================"
echo ""
read -p "Serienummer: FPS-2026-" serial
serial="FPS-2026-$serial"

if [ -z "$serial" ] || [ "$serial" = "FPS-2026-" ]; then
    echo "❌ Serienummer is verplicht!"
    exit 1
fi

echo "🔍 Controleren of $serial al in gebruik is..."

# Check bij centrale server
response=$(curl -s "https://central.flitshokje.nl/api/status/$serial")
if echo "$response" | grep -q '"client_id"'; then
    echo ""
    echo "⚠️  WAARSCHUWING: $serial bestaat al op de centrale server!"
    echo ""
    read -p "Toch doorgaan? (j/n): " confirm
    if [ "$confirm" != "j" ]; then
        echo "❌ Geannuleerd."
        exit 1
    fi
else
    echo "✅ Serienummer $serial is beschikbaar"
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
