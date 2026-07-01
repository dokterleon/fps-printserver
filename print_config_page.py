import subprocess, json, os, shutil

def run(cmd):
    return subprocess.getoutput(cmd)

def get_serial():
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "Serial" in line:
                    return line.split(":")[1].strip()
    except Exception:
        pass
    return "onbekend"

def get_version():
    try:
        with open("version.json") as f:
            return json.load(f).get("version", "—")
    except Exception:
        return "—"

def get_client_info():
    try:
        with open("logs/beacon.json") as f:
            d = json.load(f)
            return d.get("client_id","—"), d.get("name","—"), d.get("location","—")
    except Exception:
        return "—", "—", "—"

def print_config_page():
    serial          = get_serial()
    version         = get_version()
    client_id, name, location = get_client_info()
    hostname        = run("hostname").strip()
    hotspot_url     = "http://10.0.0.1"
    portal_url      = f"https://central.flitshokje.nl/status/{client_id}"
    serial_short    = serial[-12:] if len(serial) > 12 else serial

    # Achtergrond — inzoomen 120% zodat absoluut geen witte randen
    bg_src = "/home/flitshokje/flitshokje-printserver/static/config-bg.jpg"
    subprocess.getoutput("sudo rm -f /tmp/fps-bg.jpg /tmp/fps-bon.jpg /tmp/qr_*.png")
    if os.path.exists(bg_src):
        shutil.copy(bg_src, "/tmp/fps-bg.jpg")
    else:
        run("convert -size 1800x1200 gradient:'#1a2a3a-#0a1520' /tmp/fps-bg.jpg")

    run("convert /tmp/fps-bg.jpg "
        "-resize 2160x1440^ "
        "-gravity center -extent 1800x1200 "
        "/tmp/fps-bon.jpg")

    # Minder donkere overlay — 30% zodat foto mooi zichtbaar blijft
    run("convert /tmp/fps-bon.jpg "
        "-fill 'rgba(0,0,0,0.30)' "
        "-draw 'rectangle 0,0 1800,1200' "
        "/tmp/fps-bon.jpg")

    # QR codes 380x380 (vorig formaat)
    # WiFi QR code — scan om direct te verbinden met hotspot
    wifi_qr = f"WIFI:T:WPA;S:FPS Flitshokje Print Server;P:flitshokje;;"
    run(f"python3 -c \"import qrcode; qrcode.make('{wifi_qr}').save('/tmp/qr_dash.png')\"")
    run(f"python3 -c \"import qrcode; qrcode.make('{portal_url}').save('/tmp/qr_portal.png')\"")
    run("convert /tmp/qr_dash.png   -resize 380x380 -bordercolor white -border 12 /tmp/qr_dash_s.png")
    run("convert /tmp/qr_portal.png -resize 380x380 -bordercolor white -border 12 /tmp/qr_portal_s.png")

    # QR posities
    QR_Y   = 400
    QR_L_X = 60
    QR_R_X = 1310
    QR_W   = 380 + 24  # 404px

    run(f"convert /tmp/fps-bon.jpg "
        f"\\( /tmp/qr_dash_s.png \\) -geometry +{QR_L_X}+{QR_Y} -composite "
        f"/tmp/fps-bon.jpg")
    run(f"convert /tmp/fps-bon.jpg "
        f"\\( /tmp/qr_portal_s.png \\) -geometry +{QR_R_X}+{QR_Y} -composite "
        f"/tmp/fps-bon.jpg")

    # Tekst onder QR
    TXT_Y = QR_Y + QR_W + 25

    # WiFi links — grotere tekst
    run(f"convert /tmp/fps-bon.jpg "
        f"-font Helvetica-Bold -pointsize 38 -fill '#FFE000' "
        f"-gravity NorthWest -annotate +{QR_L_X}+{TXT_Y} 'WiFi Hotspot' "
        f"-font Helvetica -pointsize 34 -fill white "
        f"-annotate +{QR_L_X}+{TXT_Y+52} 'FPS Flitshokje Print Server' "
        f"-annotate +{QR_L_X}+{TXT_Y+98} 'Wachtwoord: flitshokje' "
        f"-annotate +{QR_L_X}+{TXT_Y+144} 'http://10.0.0.1' "
        f"/tmp/fps-bon.jpg")

    # Portaal rechts — grotere tekst
    run(f"convert /tmp/fps-bon.jpg "
        f"-font Helvetica-Bold -pointsize 38 -fill '#FFE000' "
        f"-gravity NorthWest -annotate +{QR_R_X}+{TXT_Y} 'FPS Status Portaal' "
        f"-font Helvetica -pointsize 32 -fill white "
        f"-annotate +{QR_R_X}+{TXT_Y+55} 'central.flitshokje.nl' "
        f"-annotate +{QR_R_X}+{TXT_Y+98} '/status/{client_id}' "
        f"/tmp/fps-bon.jpg")

    # Naam groot bovenaan
    run(f"convert /tmp/fps-bon.jpg "
        f"-font Helvetica-Bold -pointsize 68 -fill '#FFE000' "
        f"-gravity NorthWest -annotate +{QR_L_X}+18 '{name}' "
        f"/tmp/fps-bon.jpg")

    # Info blok
    run(f"convert /tmp/fps-bon.jpg "
        f"-font Helvetica-Bold -pointsize 28 -fill white "
        f"-gravity NorthWest "
        f"-annotate +{QR_L_X}+108 'Client ID : {client_id}' "
        f"-annotate +{QR_L_X}+148 'Hostname  : {hostname}' "
        f"-annotate +{QR_L_X}+188 'Locatie   : {location}' "
        f"-annotate +{QR_L_X}+228 'Serienr   : {serial_short}' "
        f"-annotate +{QR_L_X}+268 'Versie    : v{version}' "
        f"/tmp/fps-bon.jpg")

    # Print — geen snijlijn
    printer = run("lpstat -p 2>/dev/null | awk '{print $2}' | head -1").strip()
    if printer:
        run(f"lp -d {printer} -o PageSize=w288h432 -o PageRegion=w288h432 -o fit-to-page /tmp/fps-bon.jpg")
        return True, f"Configuratiebon verstuurd naar {printer}"
    return False, "Geen printer gevonden"

if __name__ == "__main__":
    ok, msg = print_config_page()
    print(msg)
