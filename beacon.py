import json, os, time, urllib.request
from datetime import datetime

# ── hardcoded centrale server config ─────────────────────────────────────────
# Niet wijzigen — alleen door FPS beheerder
CENTRAL_URL = "https://web-production-874b7.up.railway.app"
API_KEY     = "flitshokje-secret-2026"

BEACON_FILE = "logs/beacon.json"

# ── klant instellingen ────────────────────────────────────────────────────────

def _load():
    try:
        with open(BEACON_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(data):
    os.makedirs("logs", exist_ok=True)
    current = _load()
    # alleen naam, locatie en client_id opslaan — nooit url/key
    for k in ("client_id", "name", "location"):
        if k in data:
            current[k] = data[k]
    with open(BEACON_FILE, "w") as f:
        json.dump(current, f, indent=2)

def get_settings():
    s = _load()
    return {
        "client_id": s.get("client_id", ""),
        "name":      s.get("name", ""),
        "location":  s.get("location", ""),
        "active":    bool(s.get("client_id")),
    }

def is_configured():
    return bool(_load().get("client_id"))

# ── ping sturen ───────────────────────────────────────────────────────────────

def send_ping(status_data, system_data):
    s = _load()
    if not s.get("client_id"):
        return False

    printers = []
    for p in status_data.get("all_printers", []):
        printers.append({
            "printer":   p.get("printer"),
            "state":     p.get("state"),
            "remaining": p.get("remaining"),
            "low_paper": p.get("low_paper"),
            "mode":      p.get("mode_label"),
        })

    errors = []
    for p in status_data.get("all_printers", []):
        if p.get("friendly_error"):
            errors.append(f"{p['printer']}: {p['friendly_error']}")
        elif p.get("low_paper"):
            errors.append(f"{p['printer']}: Papier bijna op ({p['remaining']} resterend)")

    sys = system_data or {}

    payload = {
        "client_id": s["client_id"],
        "name":      s.get("name", s["client_id"]),
        "location":  s.get("location", "—"),
        "ip":        sys.get("ip", "—"),
        "version":   _get_version(),
        "printers":  printers,
        "temp":      sys.get("temp"),
        "uptime":    sys.get("uptime", "—"),
        "disk_pct":  sys.get("disk", {}).get("pct", 0),
        "airprint":  sys.get("airprint", False),
        "errors":    errors,
    }

    try:
        req = urllib.request.Request(
            f"{CENTRAL_URL}/api/ping",
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "X-API-Key":    API_KEY,
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False

def _get_version():
    try:
        with open("version.json") as f:
            return json.load(f).get("version", "—")
    except Exception:
        return "—"

# ── beacon loop ───────────────────────────────────────────────────────────────

def beacon_loop(status_fn, system_fn):
    while True:
        try:
            if is_configured():
                send_ping(status_fn(), system_fn())
        except Exception:
            pass
        time.sleep(300)
