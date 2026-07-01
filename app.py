from flask import Flask, render_template, redirect, jsonify, request, session, send_file
import threading, time, secrets, io
import printer, system, auth, updater, settings_manager, notifier, beacon
from config import APP_NAME, VERSION

app = Flask(__name__)
app.secret_key = "16ed352662fb8656e6755ab6ae6234cd3b3980df3d0fc84a444fd4da7ded82b0"

# ── achtergrond loops ─────────────────────────────────────────────────────────

def auto_resume_loop():
    while True:
        try:
            if settings_manager.get("auto_resume"):
                for name in printer.list_printers():
                    try:
                        s = printer.printer_status(name)
                        if s["state"] == "Paused/Error":
                            printer.resume(name)
                            if notifier.is_configured():
                                ns = notifier._load()
                                if ns.get("notify_printer_error", True):
                                    notifier.notify_printer_error(name, s.get("friendly_error") or "Printer gepauzeerd")
                    except Exception:
                        pass
        except Exception:
            pass
        time.sleep(3)

def print_count_loop():
    prev_jobs = {}
    while True:
        try:
            for name in printer.list_printers():
                s = printer.printer_status(name)
                curr = s["job_count"]
                prev = prev_jobs.get(name, curr)
                if prev > curr:
                    for _ in range(prev - curr):
                        printer._log("print", f"{name}: {s['mode_label'] or 'print'}")
                        system.increment_rol()
                prev_jobs[name] = curr
                if s["low_paper"] and notifier.is_configured():
                    ns = notifier._load()
                    if ns.get("notify_low_paper", True):
                        notifier.notify_low_paper(name, s["remaining"])
        except Exception:
            pass
        time.sleep(2)

def auto_update_loop():
    updater.auto_update_loop(settings_manager.load)

def beacon_loop():
    beacon.beacon_loop(printer.status, system.get_system_status)

# ── auth ──────────────────────────────────────────────────────────────────────

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if auth.check_password(request.form.get("password", "")):
            session["logged_in"] = True
            return redirect("/")
        error = "Ongeldig wachtwoord" if get_lang() == "nl" else "Invalid password"
    return render_template("login.html", app_name=APP_NAME, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/lang/<lang>")
def set_lang(lang):
    if lang in ("nl", "en"):
        session["lang"] = lang
    return redirect(request.referrer or "/")

def get_lang():
    return session.get("lang", settings_manager.get("language"))



# ── captive portal detectie (iOS/Android) ────────────────────────────────────

@app.route("/hotspot-detect.html")
@app.route("/library/test/success.html")
@app.route("/generate_204")
@app.route("/ncsi.txt")
@app.route("/connecttest.txt")
def captive_portal():
    return redirect("/", 302)

# ── setup ─────────────────────────────────────────────────────────────────────

def _setup_done():
    """Check of de setup al gedaan is."""
    import os
    return os.path.exists("/home/flitshokje/flitshokje-printserver/logs/beacon.json")


@app.route("/api/setup-password", methods=["POST"])
def api_setup_password():
    d  = request.json or {}
    pw = d.get("password", "")
    if pw:
        auth.set_password(pw)
    return jsonify({"ok": True})

@app.route("/setup", methods=["GET", "POST"])
def setup():
    if request.method == "POST":
        if request.form.get("install_pw") == "FPSinstall!":
            session["setup_auth"] = True
            return redirect("/setup")
        return render_template("setup_login.html", error="Ongeldig wachtwoord")
    if not session.get("setup_auth"):
        return render_template("setup_login.html", error=None)
    return render_template("setup.html")

@app.route("/api/setup", methods=["POST"])
def api_setup():
    import json as _json
    d = request.json or {}
    client_id = d.get("client_id", "").strip().replace(" ", "-")
    name      = d.get("name", "").strip()
    location  = d.get("location", "").strip()
    if not client_id or not name:
        return jsonify({"ok": False, "error": "Vul alle velden in"})
    beacon.save_settings({
        "client_id": client_id,
        "name":      name,
        "location":  location,
    })
    return jsonify({"ok": True})

# ── dashboard ─────────────────────────────────────────────────────────────────

@app.route("/")
@auth.login_required
def index():
    if not _setup_done():
        return redirect("/setup")
    return render_template("index.html", app_name=APP_NAME, version=VERSION, lang=get_lang())

@app.route("/api/status")
@auth.login_required
def api_status():
    return jsonify(printer.status())

@app.route("/api/system")
@auth.login_required
def api_system():
    return jsonify(system.get_system_status())

@app.route("/api/qr.png")
@auth.login_required
def api_qr():
    import qrcode
    url = f"http://{system._ip()}"
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

@app.route("/printer/<name>")
@auth.login_required
def printer_detail(name):
    return render_template("printer.html", app_name=APP_NAME, version=VERSION,
                           lang=get_lang(), printer_name=name)

@app.route("/api/printer/<name>")
@auth.login_required
def api_printer(name):
    try:
        return jsonify(printer.printer_status(name))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ── printer acties ────────────────────────────────────────────────────────────

@app.route("/mode/<name>/<mode>")
@auth.login_required
def set_mode(name, mode):
    printer.set_mode(name, mode)
    return redirect(request.referrer or "/")

@app.route("/resume")
@app.route("/resume/<name>")
@auth.login_required
def resume(name=None):
    printer.resume(name)
    return redirect(request.referrer or "/")

@app.route("/cancel")
@app.route("/cancel/<name>")
@auth.login_required
def cancel(name=None):
    printer.cancel_all(name)
    return redirect(request.referrer or "/")

@app.route("/restart-cups")
@auth.login_required
def restart_cups():
    printer.restart_cups()
    return redirect(request.referrer or "/")

@app.route("/test-print/<name>")
@auth.login_required
def test_print(name):
    printer.test_print(name)
    return redirect(request.referrer or "/")

@app.route("/reset-rol")
@auth.login_required
def reset_rol():
    system.reset_rol()
    return redirect("/")


@app.route("/print-config")
@auth.login_required
def print_config():
    import print_config_page
    print_config_page.print_config_page()
    return redirect("/settings")

# ── instellingen ──────────────────────────────────────────────────────────────

@app.route("/settings", methods=["GET", "POST"])
@auth.login_required
def settings():
    msg = None
    lang = get_lang()
    if request.method == "POST":
        action = request.form.get("action")
        if action == "hostname":
            name = system.set_hostname(request.form.get("hostname", ""))
            msg = f"Hostname → {name}" if name else "Ongeldige hostname"
        elif action == "password":
            pw  = request.form.get("password", "")
            pw2 = request.form.get("password2", "")
            if pw and pw == pw2:
                auth.set_password(pw)
                msg = "Wachtwoord ingesteld"
            elif pw != pw2:
                msg = "Wachtwoorden komen niet overeen"
        elif action == "disable_password":
            auth.disable()
            msg = "Wachtwoord uitgeschakeld"
        elif action == "general":
            settings_manager.save({
                "auto_update": "auto_update" in request.form,
                "auto_resume": "auto_resume" in request.form,
                "language":    request.form.get("language", "nl"),
            })
            session["lang"] = request.form.get("language", "nl")
            msg = "Opgeslagen"
        elif action == "notifications":
            notifier.save_settings({
                "gmail_user":           request.form.get("gmail_user", ""),
                "gmail_pass":           request.form.get("gmail_pass", ""),
                "to_email":             request.form.get("to_email", ""),
                "notify_low_paper":     "notify_low_paper"     in request.form,
                "notify_printer_error": "notify_printer_error" in request.form,
            })
            msg = "Notificaties opgeslagen"
        elif action == "test_notification":
            ok, result = notifier.notify_test()
            msg = f"✓ Test verstuurd" if ok else f"✕ {result}"
        elif action == "beacon":
            beacon.save_settings({
                "central_url": request.form.get("central_url", ""),
                "api_key":     request.form.get("api_key", ""),
                "client_id":   request.form.get("client_id", ""),
                "name":        request.form.get("client_name", ""),
                "location":    request.form.get("location", ""),
            })
            msg = "Centrale server instellingen opgeslagen"

    sys_info     = system.get_system_status()
    cur_settings = settings_manager.load()
    notif        = notifier.get_settings()
    beacon_cfg   = beacon.get_settings()
    return render_template("settings.html",
        app_name=APP_NAME, version=VERSION, lang=lang,
        sys=sys_info, msg=msg,
        auth_enabled=auth.is_enabled(),
        settings=cur_settings,
        notif=notif,
        beacon=beacon_cfg)


@app.route("/api/central-status")
@auth.login_required
def api_central_status():
    import urllib.request
    try:
        req = urllib.request.Request(
            "https://central.flitshokje.nl/api/ping",
            data=b'{}',
            headers={"Content-Type": "application/json", "X-API-Key": ""},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=3)
        return jsonify({"online": True})
    except Exception:
        # ping endpoint bestaat maar geeft 401 = centrale is online
        try:
            urllib.request.urlopen("https://central.flitshokje.nl", timeout=3)
            return jsonify({"online": True})
        except Exception as e:
            if "401" in str(e) or "403" in str(e):
                return jsonify({"online": True})
            return jsonify({"online": False})


# ── wifi beheer ───────────────────────────────────────────────────────────────

@app.route("/api/wifi/status")
@auth.login_required
def wifi_status():
    import subprocess, re
    out = subprocess.getoutput("iwconfig wlan1 2>/dev/null")
    connected = "ESSID" in out and "off/any" not in out
    ssid = ""
    ip = ""
    if connected:
        m = re.search(r'ESSID:"([^"]+)"', out)
        if m: ssid = m.group(1)
        ip_out = subprocess.getoutput("ip -4 addr show wlan1 2>/dev/null | grep inet")
        ip_m = re.search(r'inet ([\d.]+)', ip_out)
        if ip_m: ip = ip_m.group(1)
    return jsonify({"connected": connected, "ssid": ssid, "ip": ip})

@app.route("/api/wifi/scan")
@auth.login_required
def wifi_scan():
    import subprocess
    out = subprocess.getoutput("sudo iwlist wlan1 scan 2>/dev/null | grep ESSID")
    networks = []
    for line in out.splitlines():
        line = line.strip()
        if 'ESSID:"' in line:
            ssid = line.split('"')[1]
            if ssid and ssid not in networks:
                networks.append(ssid)
    return jsonify({"networks": networks})

@app.route("/api/wifi/connect", methods=["POST"])
@auth.login_required
def wifi_connect():
    import subprocess
    d = request.json or {}
    ssid = d.get("ssid", "")
    password = d.get("password", "")
    if not ssid:
        return jsonify({"success": False, "message": "Geen SSID opgegeven"})
    config = f'''ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1
country=NL

network={{
    ssid="{ssid}"
    psk="{password}"
    key_mgmt=WPA-PSK
}}
'''
    with open("/etc/wpa_supplicant/wpa_supplicant-wlan1.conf", "w") as f:
        f.write(config)
    subprocess.getoutput("sudo rm -f /var/run/wpa_supplicant/wlan1")
    subprocess.getoutput("sudo systemctl restart wpa_supplicant@wlan1")
    subprocess.getoutput("sudo dhcpcd wlan1")
    return jsonify({"success": True, "message": f"Verbinden met {ssid}..."})

@app.route("/api/wifi/disconnect", methods=["POST"])
@auth.login_required
def wifi_disconnect():
    import subprocess
    subprocess.getoutput("sudo ip link set wlan1 down")
    subprocess.getoutput("sudo ip link set wlan1 up")
    return jsonify({"success": True, "message": "Verbinding verbroken"})

# ── updates ───────────────────────────────────────────────────────────────────

@app.route("/api/check-update")
@auth.login_required
def api_check_update():
    return jsonify(updater.check_update())

@app.route("/api/do-update", methods=["POST"])
@auth.login_required
def api_do_update():
    return jsonify(updater.do_update())

# ── logs ──────────────────────────────────────────────────────────────────────

@app.route("/logs")
@auth.login_required
def logs():
    return render_template("logs.html", app_name=APP_NAME, version=VERSION, lang=get_lang())

@app.route("/api/logs")
@auth.login_required
def api_logs():
    import json
    try:
        with open("logs/history.json") as f:
            return jsonify(json.load(f))
    except Exception:
        return jsonify([])

# ── start ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    threading.Thread(target=auto_resume_loop, daemon=True).start()
    threading.Thread(target=print_count_loop, daemon=True).start()
    threading.Thread(target=auto_update_loop, daemon=True).start()
    threading.Thread(target=beacon_loop,      daemon=True).start()
    app.run(host="0.0.0.0", port=80)
# Bovenstaande wordt toegevoegd aan de bestaande routes sectie
