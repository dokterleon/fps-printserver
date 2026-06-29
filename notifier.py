import smtplib, json, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

NOTIF_FILE   = "logs/notifications.json"
NOTIF_LOG    = "logs/notif_log.json"

def _load():
    try:
        with open(NOTIF_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_settings(data):
    os.makedirs("logs", exist_ok=True)
    current = _load()
    current.update(data)
    with open(NOTIF_FILE, "w") as f:
        json.dump(current, f, indent=2)

def is_configured():
    s = _load()
    return bool(s.get("gmail_user") and s.get("gmail_pass") and s.get("to_email"))

def send(subject, body, force=False):
    s = _load()
    if not s.get("gmail_user") or not s.get("gmail_pass") or not s.get("to_email"):
        return False, "Niet geconfigureerd"
    if not force and _already_sent_today(subject):
        return False, "Al verstuurd vandaag"
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[FPS] {subject}"
        msg["From"]    = s["gmail_user"]
        msg["To"]      = s["to_email"]

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:480px;margin:0 auto">
          <div style="background:#FFE000;padding:16px 20px;border-radius:10px 10px 0 0">
            <strong style="font-size:16px">⚡ Flitshokje Print Server</strong>
          </div>
          <div style="background:#f9f9f9;padding:20px;border-radius:0 0 10px 10px;border:1px solid #eee">
            <p style="font-size:15px;margin:0 0 12px">{body}</p>
            <p style="font-size:12px;color:#999;margin:0">{datetime.now().strftime('%d-%m-%Y %H:%M')}</p>
          </div>
        </div>
        """
        msg.attach(MIMEText(body, "plain"))
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(s["gmail_user"], s["gmail_pass"])
            server.sendmail(s["gmail_user"], s["to_email"], msg.as_string())

        _log_sent(subject)
        return True, "Verstuurd"
    except Exception as e:
        return False, str(e)

def notify_low_paper(printer_name, remaining):
    subject = f"Papier bijna op — {printer_name}"
    body    = f"De papierrol van {printer_name} heeft nog {remaining} prints resterend.\n\nVervang de rol om printproblemen te voorkomen."
    return send(subject, body)

def notify_printer_error(printer_name, error):
    subject = f"Printer fout — {printer_name}"
    body    = f"Printer {printer_name} heeft een fout:\n\n{error}\n\nControleer de printer."
    return send(subject, body)

def notify_test(to_email=None):
    s = _load()
    if to_email:
        orig = s.get("to_email")
        s["to_email"] = to_email
        with open(NOTIF_FILE, "w") as f:
            json.dump(s, f)
    result = send("Test notificatie", "Dit is een test van de Flitshokje Print Server. Notificaties werken correct!", force=True)
    if to_email and orig:
        s["to_email"] = orig
        with open(NOTIF_FILE, "w") as f:
            json.dump(s, f)
    return result

def _already_sent_today(subject):
    log = _read_log()
    today = datetime.now().strftime("%d-%m-%Y")
    return any(e.get("subject") == subject and e.get("date") == today for e in log)

def _log_sent(subject):
    os.makedirs("logs", exist_ok=True)
    log = _read_log()
    log.insert(0, {
        "subject": subject,
        "date":    datetime.now().strftime("%d-%m-%Y"),
        "time":    datetime.now().strftime("%H:%M"),
    })
    with open(NOTIF_LOG, "w") as f:
        json.dump(log[:100], f)

def _read_log():
    try:
        with open(NOTIF_LOG) as f:
            return json.load(f)
    except Exception:
        return []

def get_log():
    return _read_log()

def get_settings():
    s = _load()
    # verberg het wachtwoord
    return {
        "gmail_user":   s.get("gmail_user", ""),
        "to_email":     s.get("to_email", ""),
        "configured":   is_configured(),
        "low_paper":    s.get("notify_low_paper", True),
        "printer_error":s.get("notify_printer_error", True),
    }
