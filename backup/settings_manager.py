import json, os

SETTINGS_FILE = "logs/settings.json"

DEFAULTS = {
    "auto_update":   False,
    "language":      "nl",
    "auto_resume":   True,
    "low_paper_threshold": 20,
}

def load():
    try:
        with open(SETTINGS_FILE) as f:
            s = json.load(f)
            # vul ontbrekende keys aan met defaults
            for k, v in DEFAULTS.items():
                if k not in s:
                    s[k] = v
            return s
    except Exception:
        return DEFAULTS.copy()

def save(data):
    os.makedirs("logs", exist_ok=True)
    current = load()
    current.update(data)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(current, f, indent=2)
    return current

def get(key):
    return load().get(key, DEFAULTS.get(key))
