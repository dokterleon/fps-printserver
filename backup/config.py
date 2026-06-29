APP_NAME    = "Flitshokje Print Server"
VERSION     = "2.1.0"
PRINTER     = "Flitshokje-CX02"
LOG_FILE    = "logs/history.json"
STATS_FILE  = "logs/stats.json"
AUTH_FILE   = "logs/auth.json"

MODES = {
    "4x6": {
        "pagesize": "w288h432",
        "label":    "4×6 / 10×15",
        "desc":     "Hele foto · geen snijlijn",
        "cut":      False,
    },
    "2x6": {
        "pagesize": "w288h432-div2",
        "label":    "2×6 strip ×2",
        "desc":     "Twee strips · met snijlijn",
        "cut":      True,
    },
}

CUPS_ERROR_MAP = {
    "media empty":        "Papier op — vervang de rol",
    "paper empty":        "Papier op — vervang de rol",
    "out of paper":       "Papier op — vervang de rol",
    "cover open":         "Klep open — sluit de printer",
    "door open":          "Klep open — sluit de printer",
    "offline":            "Printer offline — controleer USB",
    "not connected":      "Printer niet verbonden — controleer USB",
    "ink empty":          "Lint op — vervang het lint",
    "ribbon empty":       "Lint op — vervang het lint",
    "media jam":          "Papierstoring — open de klep",
    "paper jam":          "Papierstoring — open de klep",
    "paused":             "Gepauzeerd — klik Resume",
    "stopped":            "Gestopt — klik Resume",
    "disabled":           "Uitgeschakeld — klik Resume",
}
GITHUB_TOKEN = "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"
