import json, os, hashlib, secrets
from functools import wraps
from flask import request, redirect, session
from config import AUTH_FILE

def _load():
    try:
        with open(AUTH_FILE) as f:
            return json.load(f)
    except Exception:
        return {"enabled": False, "hash": "", "salt": ""}

def _save(data):
    os.makedirs("logs", exist_ok=True)
    with open(AUTH_FILE, "w") as f:
        json.dump(data, f)

def is_enabled():
    return _load().get("enabled", False)

def check_password(pw):
    d = _load()
    h = hashlib.sha256((d["salt"] + pw).encode()).hexdigest()
    return h == d["hash"]

def set_password(pw):
    salt = secrets.token_hex(16)
    h    = hashlib.sha256((salt + pw).encode()).hexdigest()
    _save({"enabled": True, "hash": h, "salt": salt})

def disable():
    _save({"enabled": False, "hash": "", "salt": ""})

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if is_enabled() and not session.get("logged_in"):
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated
