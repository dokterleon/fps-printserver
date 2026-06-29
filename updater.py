import subprocess, json, os, threading
from datetime import datetime

REPO      = "dokterleon/fps-printserver"
LOG_FILE  = "logs/history.json"

def run(cmd):
    return subprocess.getoutput(cmd)

def _log(detail):
    os.makedirs("logs", exist_ok=True)
    try:
        with open(LOG_FILE) as f:
            log = json.load(f)
    except Exception:
        log = []
    log.insert(0, {
        "time":   datetime.now().strftime("%d-%m %H:%M"),
        "event":  "update",
        "detail": detail,
    })
    with open(LOG_FILE, "w") as f:
        json.dump(log[:500], f)

def get_local_version():
    try:
        with open("version.json") as f:
            return json.load(f)
    except Exception:
        return {"version": "2.2.0"}

def get_remote_version():
    try:
        out = run(f"curl -s --max-time 5 https://raw.githubusercontent.com/{REPO}/main/version.json")
        data = json.loads(out)
        return {"version": data.get("version", "—"), "available": True}
    except Exception:
        return {"available": False, "error": "Geen verbinding met GitHub"}

def _version_tuple(v):
    try:
        return tuple(int(x) for x in str(v).split("."))
    except Exception:
        return (0, 0, 0)

def check_update():
    local  = get_local_version()
    remote = get_remote_version()

    if not remote.get("available"):
        return {
            "status":     "error",
            "message":    remote.get("error", "Onbekende fout"),
            "local":      local,
            "remote":     None,
            "has_update": False,
        }

    has_update = _version_tuple(remote["version"]) > _version_tuple(local.get("version","0.0.0"))

    return {
        "status":     "update_available" if has_update else "up_to_date",
        "message":    f"Versie {remote['version']} beschikbaar" if has_update else f"Up to date (v{local.get('version','')})",
        "local":      local,
        "remote":     remote,
        "has_update": has_update,
    }

def do_update():
    try:
        _log("Update gestart...")
        out = run("git -C /home/flitshokje/flitshokje-printserver pull origin main 2>&1")
        if "Already up to date" in out:
            _log("Al up to date")
            return {"success": True, "message": "Al up to date", "output": out}
        _log(f"Update geïnstalleerd")
        threading.Timer(1.5, lambda: run("systemctl restart flitshokje-printserver")).start()
        return {"success": True, "message": "Update geïnstalleerd, server herstart...", "output": out}
    except Exception as e:
        _log(f"Update mislukt: {e}")
        return {"success": False, "message": str(e), "output": ""}

def auto_update_loop(settings_fn):
    import time
    while True:
        now = datetime.now()
        if now.hour == 3 and now.minute == 0:
            try:
                if settings_fn().get("auto_update", False):
                    result = check_update()
                    if result.get("has_update"):
                        do_update()
            except Exception:
                pass
            time.sleep(61)
        time.sleep(30)
