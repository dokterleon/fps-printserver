import subprocess, os, re, json, socket
from datetime import datetime
from config import STATS_FILE

def run(cmd):
    return subprocess.getoutput(cmd)

def get_system_status():
    return {
        "airprint":  _airprint(),
        "network":   _network(),
        "cups":      _cups(),
        "temp":      _temp(),
        "uptime":    _uptime(),
        "disk":      _disk(),
        "ip":        _ip(),
        "hostname":  _hostname(),
        "prints":    _print_stats(),
        "rol":       _rol_stats(),
    }

def _airprint():
    return run("systemctl is-active avahi-daemon").strip() == "active"

def _network():
    # check gateway bereikbaar (werkt zonder internet)
    gw = run("ip route | grep default | awk '{print $3}' | head -1").strip()
    if not gw:
        return {"connected": False, "type": "none", "ip": None, "gateway": None}

    # ping gateway
    result = run(f"ping -c 1 -W 1 {gw} 2>/dev/null | grep -c '1 received'").strip()
    connected = result == "1"

    # eth0 of wlan0?
    eth_up  = "UP" in run("ip link show eth0 2>/dev/null")
    wlan_up = "UP" in run("ip link show wlan0 2>/dev/null") and "NO-CARRIER" not in run("ip link show wlan0 2>/dev/null")
    ntype   = "ethernet" if eth_up else "wifi" if wlan_up else "none"

    return {"connected": connected, "type": ntype, "gateway": gw}

def _cups():
    out = run("curl -s -o /dev/null -w '%{http_code}' http://localhost:631 --max-time 2")
    return out.strip() == "200"

def _temp():
    try:
        raw = open("/sys/class/thermal/thermal_zone0/temp").read().strip()
        return round(int(raw) / 1000, 1)
    except Exception:
        return None

def _uptime():
    try:
        with open("/proc/uptime") as f:
            secs = float(f.read().split()[0])
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        if h >= 24:
            return f"{h//24}d {h%24}u"
        return f"{h}u {m}m"
    except Exception:
        return "—"

def _disk():
    out = run("df -h / | tail -1").split()
    if len(out) >= 5:
        return {"used": out[2], "total": out[1], "pct": int(out[4].replace("%", ""))}
    return {"used": "—", "total": "—", "pct": 0}

def _ip():
    # eth0 eerst, anders wlan0
    for iface in ["eth0", "wlan0"]:
        out = run(f"ip -4 addr show {iface} 2>/dev/null | grep 'inet ' | awk '{{print $2}}' | cut -d/ -f1").strip()
        if out:
            return out
    return run("hostname -I").strip().split()[0] if run("hostname -I").strip() else "—"

def _hostname():
    return run("hostname").strip()

def _print_stats():
    try:
        with open("logs/history.json") as f:
            history = json.load(f)
    except Exception:
        return {"today": 0, "total": 0, "last": None}
    today = datetime.now().strftime("%d-%m")
    today_count = sum(1 for h in history if h.get("event") == "print" and h.get("time","").startswith(today))
    total       = sum(1 for h in history if h.get("event") == "print")
    last        = next((h["time"] for h in history if h.get("event") == "print"), None)
    return {"today": today_count, "total": total, "last": last}

def _rol_stats():
    try:
        with open(STATS_FILE) as f:
            return json.load(f)
    except Exception:
        return {"since_roll": 0, "roll_date": None}

def reset_rol():
    os.makedirs("logs", exist_ok=True)
    data = {"since_roll": 0, "roll_date": datetime.now().strftime("%d-%m-%Y %H:%M")}
    with open(STATS_FILE, "w") as f:
        json.dump(data, f)

def increment_rol():
    d = _rol_stats()
    d["since_roll"] = d.get("since_roll", 0) + 1
    os.makedirs("logs", exist_ok=True)
    with open(STATS_FILE, "w") as f:
        json.dump(d, f)

def set_hostname(name):
    safe = re.sub(r"[^a-zA-Z0-9\-]", "", name)[:32]
    if not safe:
        return False
    run(f"hostnamectl set-hostname {safe}")
    return safe
