import subprocess, re, json, os
from datetime import datetime
from config import LOG_FILE, CUPS_ERROR_MAP

def run(cmd):
    return subprocess.getoutput(cmd)

# ── printer detectie ──────────────────────────────────────────────────────────

BRAND_MODES = {
    "citizen": {
        "4x6":  {"pagesize": "w288h432",      "label": "4×6 / 10×15", "desc": "Hele foto · geen snijlijn", "cut": False},
        "2x6":  {"pagesize": "w288h432-div2", "label": "2×6 strip ×2", "desc": "Twee strips · met snijlijn", "cut": True},
    },
    "dnp": {
        "4x6":  {"pagesize": "w288h432",      "label": "4×6 / 10×15", "desc": "Hele foto",        "cut": False},
        "5x7":  {"pagesize": "w360h504",      "label": "5×7 / 13×18", "desc": "Middelgroot",      "cut": False},
        "6x8":  {"pagesize": "w432h576",      "label": "6×8 / 15×20", "desc": "Groot formaat",    "cut": False},
        "2x6":  {"pagesize": "w288h432-div2", "label": "2×6 strip ×2","desc": "Twee strips",      "cut": True},
    },
    "mitsubishi": {
        "4x6":  {"pagesize": "w288h432",      "label": "4×6 / 10×15", "desc": "Hele foto",        "cut": False},
        "5x7":  {"pagesize": "w360h504",      "label": "5×7 / 13×18", "desc": "Middelgroot",      "cut": False},
        "6x8":  {"pagesize": "w432h576",      "label": "6×8 / 15×20", "desc": "Groot formaat",    "cut": False},
        "6x9":  {"pagesize": "w432h648",      "label": "6×9 / 15×23", "desc": "Extra groot",      "cut": False},
    },
    "default": {
        "4x6":  {"pagesize": "w288h432",      "label": "4×6 / 10×15", "desc": "Standaard foto",   "cut": False},
        "5x7":  {"pagesize": "w360h504",      "label": "5×7 / 13×18", "desc": "Middelgroot",      "cut": False},
        "6x8":  {"pagesize": "w432h576",      "label": "6×8 / 15×20", "desc": "Groot formaat",    "cut": False},
    },
}

def detect_brand(printer_name):
    low = printer_name.lower()
    if "citizen" in low or "cx" in low:
        return "citizen"
    if "dnp" in low or "ds6" in low or "ds-r" in low or "rx1" in low:
        return "dnp"
    if "mitsubishi" in low or "cp-" in low or "cp9" in low:
        return "mitsubishi"
    # check PPD beschrijving ook
    ppd = run(f"lpoptions -p {printer_name} -l 2>/dev/null | head -5")
    low_ppd = ppd.lower()
    if "citizen" in low_ppd: return "citizen"
    if "dnp" in low_ppd:     return "dnp"
    if "mitsubishi" in low_ppd: return "mitsubishi"
    return "default"

def get_modes_for_printer(printer_name):
    """Haal beschikbare PageSize opties op uit PPD en filter op bekende modes."""
    brand  = detect_brand(printer_name)
    modes  = BRAND_MODES.get(brand, BRAND_MODES["default"])
    # filter op wat de printer echt ondersteunt via lpoptions
    avail  = run(f"lpoptions -p {printer_name} -l 2>/dev/null | grep '^PageSize'")
    if not avail:
        return modes
    supported = {}
    for key, m in modes.items():
        if m["pagesize"] in avail:
            supported[key] = m
    return supported if supported else modes

def list_printers():
    """Geef alle CUPS printers terug."""
    out = run("lpstat -p 2>/dev/null")
    printers = []
    for line in out.splitlines():
        m = re.match(r"printer (\S+)", line)
        if m:
            printers.append(m.group(1))
    return printers

# ── mode wisselen ─────────────────────────────────────────────────────────────

def set_mode(printer_name, mode_key):
    modes = get_modes_for_printer(printer_name)
    if mode_key not in modes:
        return False
    ps = modes[mode_key]["pagesize"]
    run(f"lpoptions -p {printer_name} -o PageSize={ps} -o PageRegion={ps}")
    cups_dir = "/root/.cups"
    os.makedirs(cups_dir, exist_ok=True)
    # update regel voor deze printer in lpoptions file
    lpopts_file = f"{cups_dir}/lpoptions"
    lines = []
    try:
        with open(lpopts_file) as f:
            lines = [l for l in f.readlines() if not l.startswith(f"Dest {printer_name} ")]
    except Exception:
        pass
    lines.append(f"Dest {printer_name} PageSize={ps} PageRegion={ps}\n")
    with open(lpopts_file, "w") as f:
        f.writelines(lines)
    _enable(printer_name)
    _log("mode", f"{printer_name}: mode → {modes[mode_key]['label']}")
    return True

# ── printer acties ────────────────────────────────────────────────────────────

def _enable(printer_name):
    run(f"cupsenable  {printer_name}")
    run(f"cupsaccept  {printer_name}")

def resume(printer_name=None):
    printers = [printer_name] if printer_name else list_printers()
    for p in printers:
        _enable(p)
    _log("resume", f"Hervat: {', '.join(printers)}")

def cancel_all(printer_name=None):
    printers = [printer_name] if printer_name else list_printers()
    for p in printers:
        run(f"cancel -a {p}")
    _log("cancel", f"Queue geleegd: {', '.join(printers)}")

def restart_cups():
    run("systemctl restart cups")
    _log("cups", "CUPS herstart")

def test_print(printer_name):
    run("convert -size 1200x1800 xc:white "
        "-gravity center -pointsize 90 -fill black "
        f"-annotate 0 'FPS\\nTEST\\n{printer_name}' /tmp/fps-test.jpg")
    run(f"lp -d {printer_name} /tmp/fps-test.jpg")
    _log("test_print", f"Test print → {printer_name}")

# ── status per printer ────────────────────────────────────────────────────────

def _friendly_error(raw):
    low = raw.lower()
    for key, msg in CUPS_ERROR_MAP.items():
        if key in low:
            return msg
    return None

def printer_status(name):
    options = run(f"lpoptions -p {name} 2>/dev/null")
    stat    = run(f"lpstat -p {name} -l 2>/dev/null")
    queue   = run(f"lpstat -o {name} 2>/dev/null")

    low = stat.lower()
    if "printing" in low:
        state = "Printing"
    elif "disabled" in low or "paused" in low or "stopped" in low or "paper" in low:
        state = "Paused/Error"
    else:
        state = "Ready"

    friendly_error = _friendly_error(stat) if state == "Paused/Error" else None
    remaining_raw  = re.search(r"marker-message='([^']+)'", options)
    media          = re.search(r"marker-names='([^']+)'",   options)
    pagesize       = re.search(r"PageSize=([^ ]+)",          options)
    marker_level   = re.search(r"marker-levels=(\d+)",       options)

    # resterende prints
    rem = ""
    if remaining_raw:
        raw_rem = remaining_raw.group(1).strip().strip("'").strip()
        m = re.search(r'\d+', raw_rem)
        rem = m.group(0) if m else raw_rem

    low_paper = False
    try:
        low_paper = int(rem) < 20
    except Exception:
        pass

    # huidige mode
    modes = get_modes_for_printer(name)
    current_mode = None
    current_mode_label = "—"
    if pagesize:
        ps = pagesize.group(1).strip()
        for key, m in modes.items():
            if m["pagesize"] == ps:
                current_mode = key
                current_mode_label = m["label"]
                break

    jobs = [l.strip() for l in (queue or "").splitlines() if l.strip()]

    return {
        "printer":        name,
        "brand":          detect_brand(name),
        "state":          state,
        "friendly_error": friendly_error,
        "media":          media.group(1) if media else "—",
        "remaining":      rem or "—",
        "low_paper":      low_paper,
        "marker_level":   int(marker_level.group(1)) if marker_level else None,
        "current_mode":   current_mode,
        "mode_label":     current_mode_label,
        "modes":          modes,
        "jobs":           jobs,
        "job_count":      len(jobs),
        "raw_status":     stat,
    }

def status():
    printers = list_printers()
    all_status = []
    for name in printers:
        try:
            all_status.append(printer_status(name))
        except Exception as e:
            all_status.append({
                "printer": name, "brand": "unknown",
                "state": "Unknown", "friendly_error": None,
                "media": "—", "remaining": "—", "low_paper": False,
                "marker_level": None, "current_mode": None,
                "mode_label": "—", "modes": {}, "jobs": [],
                "job_count": 0, "raw_status": str(e),
            })

    result = {
        "all_printers": all_status,
        "history":      _read_log(),
    }
    return result

    # hoofd printer = eerste in lijst
    main = all_status[0] if all_status else {}
    main["all_printers"] = all_status
    main["history"]      = _read_log()
    return main

# ── logging ───────────────────────────────────────────────────────────────────

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
