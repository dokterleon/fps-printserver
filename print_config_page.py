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

    # Temp bestanden opruimen
    subprocess.getoutput("sudo rm -f /tmp/fps-bg.jpg /tmp/fps-bon.jpg /tmp/qr_*.png /tmp/fps_logo*.png")

    # Achtergrond
    bg_src = "/home/flitshokje/flitshokje-printserver/static/config-bg.jpg"
    if os.path.exists(bg_src):
        shutil.copy(bg_src, "/tmp/fps-bg.jpg")
    else:
        run("convert -size 1800x1200 gradient:'#0a1520-#1a2a3a' /tmp/fps-bg.jpg")

    # Inzoomen 120% — geen witte randen
    run("convert /tmp/fps-bg.jpg "
        "-resize 2160x1440^ "
        "-gravity center -extent 1800x1200 "
        "/tmp/fps-bon.jpg")

    # Donkere overlay 30%
    run("convert /tmp/fps-bon.jpg "
        "-fill 'rgba(0,0,0,0.30)' "
        "-draw 'rectangle 0,0 1800,1200' "
        "/tmp/fps-bon.jpg")

    # Logo rechtsonder plaatsen
    logo_src = "/home/flitshokje/flitshokje-printserver/static/fps_logo_bon.png"
    if os.path.exists(logo_src):
        run(f"convert /tmp/fps-bon.jpg "
            f"\( {logo_src} -resize 900x340 \) -geometry +40+20 -composite "
            f"/tmp/fps-bon.jpg")
    else:
        # Fallback tekst logo
        run("convert /tmp/fps-bon.jpg "
            "-font Helvetica-Bold -pointsize 36 -fill '#00AAFF' "
            "-gravity SouthEast -annotate +20+30 'FPS' "
            "-font Helvetica -pointsize 20 -fill white "
            "-gravity SouthEast -annotate +20+10 'Flitshokje.nl' "
            "/tmp/fps-bon.jpg")

    # QR codes 380x380
    run(f"python3 -c \"import qrcode; qrcode.make('WIFI:T:WPA;S:FPS Flitshokje Print Server;P:flitshokje;;').save('/tmp/qr_dash.png')\"")
    run(f"python3 -c \"import qrcode; qrcode.make('{portal_url}').save('/tmp/qr_portal.png')\"")
    run("convert /tmp/qr_dash.png   -resize 380x380 -bordercolor white -border 12 /tmp/qr_dash_s.png")
    run("convert /tmp/qr_portal.png -resize 380x380 -bordercolor white -border 12 /tmp/qr_portal_s.png")

    QR_Y   = 400
    QR_L_X = 60
    QR_R_X = 1310
    QR_W   = 404

    run(f"convert /tmp/fps-bon.jpg "
        f"\\( /tmp/qr_dash_s.png \\) -geometry +{QR_L_X}+{QR_Y} -composite "
        f"/tmp/fps-bon.jpg")
    run(f"convert /tmp/fps-bon.jpg "
        f"\\( /tmp/qr_portal_s.png \\) -geometry +{QR_R_X}+{QR_Y} -composite "
        f"/tmp/fps-bon.jpg")

    TXT_Y = QR_Y + QR_W + 25

    # WiFi links onder QR
    run(f"convert /tmp/fps-bon.jpg "
        f"-font Helvetica-Bold -pointsize 38 -fill '#00AAFF' "
        f"-gravity NorthWest -annotate +{QR_L_X}+{TXT_Y} 'WiFi Hotspot' "
        f"-font Helvetica -pointsize 34 -fill white "
        f"-annotate +{QR_L_X}+{TXT_Y+52} 'FPS Flitshokje Print Server' "
        f"-annotate +{QR_L_X}+{TXT_Y+98} 'Wachtwoord: flitshokje' "
        f"-annotate +{QR_L_X}+{TXT_Y+144} 'http://10.0.0.1' "
        f"/tmp/fps-bon.jpg")

    # Portaal rechts onder QR
    run(f"convert /tmp/fps-bon.jpg "
        f"-font Helvetica-Bold -pointsize 38 -fill '#00AAFF' "
        f"-gravity NorthWest -annotate +{QR_R_X}+{TXT_Y} 'FPS Status Portaal' "
        f"-font Helvetica -pointsize 32 -fill white "
        f"-annotate +{QR_R_X}+{TXT_Y+55} 'central.flitshokje.nl' "
        f"-annotate +{QR_R_X}+{TXT_Y+98} '/status/{client_id}' "
        f"/tmp/fps-bon.jpg")

    # Info rechts boven
    run(f"convert /tmp/fps-bon.jpg "
        f"-font Helvetica-Bold -pointsize 30 -fill '#00AAFF' "
        f"-gravity NorthEast -annotate +60+20 '{name}' "
        f"-font Helvetica-Bold -pointsize 24 -fill white "
        f"-gravity NorthEast -annotate +60+70 'Client ID : {client_id}' "
        f"-annotate +60+105 'Hostname  : {hostname}' "
        f"-annotate +60+140 'Locatie   : {location}' "
        f"-annotate +60+175 'Serienr   : {serial_short}' "
        f"-annotate +60+210 'Versie    : v{version}' "
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
