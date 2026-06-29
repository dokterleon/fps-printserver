import subprocess, re, json, os
from datetime import datetime
from config import PRINTER, MODES, LOG_FILE, CUPS_ERROR_MAP

def run(cmd):
    return subprocess.getoutput(cmd)

def set_mode(mode_key):
    if mode_key not in MODES:
        return False
    ps = MODES[mode_key]["pagesize"]
    run(f"lpoptions -p {PRINTER} -o PageSize={ps} -o PageRegion={ps}")
    os.makedirs("/root/.cups", exist_ok=True)
    with open("/root/.cups/lpoptions", "w") as f:
        f.write(f"Dest {PRINTER} PageSize={ps} PageRegion={ps}\n")
    _enable()
    _log("mode", f"Mode gewijzigd naar {MODES[mode_key]['label']}")
    return True

def _enable():
    run(f"cupsenable  {PRINTER}")
    run(f"cupsaccept  {PRINTER}")

def resume():
    _enable()
    _log("resume", "Printer hervat")

def cancel_all():
    run(f"cancel -a {PRINTER}")
    _log("cancel", "Wachtrij geleegd")

def restart_cups():
    run("systemctl restart cups")
    _log("cups", "CUPS herstart")

def test_print():
    run("convert -size 1200x1800 xc:white "
        "-gravity center -pointsize 90 -fill black "
        "-annotate 0 'FLITSHOKJE\\nTEST PRINT' /tmp/fps-test.jpg")
    run(f"lp -d {PRINTER} /tmp/fps-test.jpg")
    _log("test_print", "Test print verstuurd")

def _friendly_error(raw):
    low = raw.lower()
    for key, msg in CUPS_ERROR_MAP.items():
        if key in low:
            return msg
    return None

def status():
    options = run(f"lpoptions -p {PRINTER}")
    stat    = run(f"lpstat -p {PRINTER} -l")
    queue   = run(f"lpstat -o {PRINTER}")

    low = stat.lower()
    if "printing" in low:
        state = "Printing"
    elif "disabled" in low or "paused" in low or "stopped" in low or "paper" in low:
        state = "Paused/Error"
    else:
        state = "Ready"

    friendly_error = _friendly_error(stat) if state == "Paused/Error" else None

    remaining = re.search(r"marker-message='([^']+)'", options)
    media     = re.search(r"marker-names='([^']+)'",   options)
    pagesize  = re.search(r"PageSize=([^ ]+)",          options)

    current_mode = None
    current_mode_label = "—"
    if pagesize:
        ps = pagesize.group(1).strip()
        for key, m in MODES.items():
            if m["pagesize"] == ps:
                current_mode = key
                current_mode_label = m["label"]
                break

    raw_rem = remaining.group(1).strip().strip("'").strip()
    m = re.search(r'\d+', raw_rem)
    rem = m.group(0) if m else raw_rem


    # lage papier waarschuwing
    low_paper = False
    try:
        low_paper = int(rem) < 20
    except Exception:
        pass

    jobs = [l.strip() for l in (queue or "").splitlines() if l.strip()]

    return {
        "printer":       PRINTER,
        "state":         state,
        "friendly_error": friendly_error,
        "media":         media.group(1) if media else "—",
        "remaining":     rem or "—",
        "low_paper":     low_paper,
        "current_mode":  current_mode,
        "mode_label":    current_mode_label,
        "jobs":          jobs,
        "job_count":     len(jobs),
        "raw_status":    stat,
        "history":       _read_log(),
    }

def _log(event, detail=""):
    os.makedirs("logs", exist_ok=True)
    log = _read_log()
    log.insert(0, {
        "time":   datetime.now().strftime("%d-%m %H:%M"),
        "event":  event,
        "detail": detail,
    })
    with open(LOG_FILE, "w") as f:
        json.dump(log[:500], f)

def _read_log():
    try:
        with open(LOG_FILE) as f:
            return json.load(f)
    except Exception:
        return []
