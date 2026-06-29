import subprocess, json, os, threading
from datetime import datetime

REPO       = "dokterleon/fps-printserver"
VERSION_FILE = "version.json"
LOG_FILE   = "logs/history.json"

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
        with open(VERSION_FILE) as f:
            return json.load(f)
    except Exception:
        return {"version": "2.1.0", "commit": None, "date": None}

def get_remote_version():
    """Haal laatste commit info op via GitHub API."""
    try:
        out = run(f"curl -s --max-time 5 https://api.github.com/repos/{REPO}/commits/main")
        data = json.loads(out)
        commit  = data["sha"][:7]
        message = data["commit"]["message"].split("\n")[0]
        date    = data["commit"]["committer"]["date"][:10]
        # versienummer uit version.json op GitHub
        vout = run(f"curl -s --max-time 5 https://raw.githubusercontent.com/{REPO}/main/version.json")
        vdata = json.loads(vout)
        version = vdata.get("version", "—")
        return {
            "version": version,
            "commit":  commit,
            "message": message,
            "date":    date,
            "available": True,
        }
    except Exception:
        return {"available": False, "error": "Geen verbinding met GitHub"}

def check_update():
    """Vergelijk lokale versie met remote."""
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
    has_update = remote["commit"] != local.get("commit")
    return {
        "status":     "update_available" if has_update else "up_to_date",
        "message":    f"Versie {remote['version']} beschikbaar" if has_update else "Up to date",
        "local":      local,
        "remote":     remote,
        "has_update": has_update,
    }

def do_update():
    """Pull latest van GitHub en herstart service."""
    try:
        _log("Update gestart...")
        out = run("git -C /home/flitshokje/flitshokje-printserver pull origin main 2>&1")
        if "Already up to date" in out:
            _log("Al up to date")
            return {"success": True, "message": "Al up to date", "output": out}
        _log(f"Update geïnstalleerd: {out[:100]}")
        # herstart service na 1 seconde (zodat response nog terugkomt)
        threading.Timer(1.5, lambda: run("systemctl restart flitshokje-printserver")).start()
        return {"success": True, "message": "Update geïnstalleerd, server herstart...", "output": out}
    except Exception as e:
        _log(f"Update mislukt: {e}")
        return {"success": False, "message": str(e), "output": ""}

def save_local_version(commit, version):
    with open(VERSION_FILE, "w") as f:
        json.dump({
            "version": version,
            "commit":  commit,
            "date":    datetime.now().strftime("%Y-%m-%d"),
        }, f)

# ── auto-update scheduler ─────────────────────────────────────────────────────

def auto_update_loop(settings_fn):
    """Draait als daemon thread, checkt elke nacht om 03:00."""
    import time
    while True:
        now = datetime.now()
        # check om 03:00
        if now.hour == 3 and now.minute == 0:
            try:
                settings = settings_fn()
                if settings.get("auto_update", False):
                    result = check_update()
                    if result.get("has_update"):
                        do_update()
            except Exception:
                pass
            time.sleep(61)  # voorkom dubbele trigger in dezelfde minuut
        time.sleep(30)
