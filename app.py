from flask import Flask, render_template, redirect, jsonify, request, session, send_file
import threading, time, secrets, io
import printer, system, auth
from config import APP_NAME, VERSION

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)

def auto_resume_loop():
    while True:
        try:
            s = printer.status()
            if s["state"] == "Paused/Error":
                printer.resume()
        except Exception:
            pass
        time.sleep(3)

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        if auth.check_password(request.form.get("password", "")):
            session["logged_in"] = True
            return redirect("/")
        error = "Ongeldig wachtwoord"
    return render_template("login.html", app_name=APP_NAME, error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/")
@auth.login_required
def index():
    return render_template("index.html", app_name=APP_NAME, version=VERSION)

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
    ip  = system._ip()
    url = f"http://{ip}"
    img = qrcode.make(url)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")

@app.route("/mode/<mode>")
@auth.login_required
def set_mode(mode):
    printer.set_mode(mode)
    return redirect("/")

@app.route("/resume")
@auth.login_required
def resume():
    printer.resume()
    return redirect("/")

@app.route("/cancel")
@auth.login_required
def cancel():
    printer.cancel_all()
    return redirect("/")

@app.route("/restart-cups")
@auth.login_required
def restart_cups():
    printer.restart_cups()
    return redirect("/")

@app.route("/test-print")
@auth.login_required
def test_print():
    printer.test_print()
    return redirect("/")

@app.route("/reset-rol")
@auth.login_required
def reset_rol():
    system.reset_rol()
    return redirect("/")

@app.route("/settings", methods=["GET", "POST"])
@auth.login_required
def settings():
    msg = None
    if request.method == "POST":
        action = request.form.get("action")
        if action == "hostname":
            name = system.set_hostname(request.form.get("hostname", ""))
            msg = f"Hostname gewijzigd naar {name}" if name else "Ongeldige hostname"
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
    sys = system.get_system_status()
    return render_template("settings.html",
        app_name=APP_NAME, version=VERSION,
        sys=sys, msg=msg, auth_enabled=auth.is_enabled())

@app.route("/logs")
@auth.login_required
def logs():
    return render_template("logs.html", app_name=APP_NAME, version=VERSION)

@app.route("/api/logs")
@auth.login_required
def api_logs():
    import json
    try:
        with open("logs/history.json") as f:
            return jsonify(json.load(f))
    except Exception:
        return jsonify([])

if __name__ == "__main__":
    threading.Thread(target=auto_resume_loop, daemon=True).start()
    app.run(host="0.0.0.0", port=80)
