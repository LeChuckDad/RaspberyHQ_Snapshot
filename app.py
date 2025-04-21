from flask import Flask, render_template, Response, jsonify, request, send_file, abort
import threading
import subprocess
import time
import os
import cv2
import glob

app = Flask(__name__)

lock = threading.Lock()
CAPTURE_DIR = "./captures"
camera_running = False
live_process = None

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_video_feed')
def start_video_feed():
    global live_process

    command = [
        'libcamera-vid',
        '-t', '0',
        '--width', '640',
        '--height', '480',
        '--codec', 'mjpeg',
        '--inline',
        '-o', '-'
    ]

    live_process = subprocess.Popen(command, stdout=subprocess.PIPE)

    def generate():
        boundary = b"--frame\r\n"
        global live_process

        while True:
            # Prüfe ob der Prozess überhaupt läuft
            if live_process is None or live_process.poll() is not None:
                break

            frame = b''
            while True:
                if live_process is None:
                    break
                byte = live_process.stdout.read(1)
                if not byte:
                    break
                frame += byte
                if frame.endswith(b'\xff\xd9'):
                    break

            if frame:
                yield (
                    boundary +
                    b"Content-Type: image/jpeg\r\n\r\n" +
                    frame +
                    b"\r\n"
                )
 
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/stop_video_feed', methods=['POST'])
def stop_video_feed():
    global live_process
    if live_process and live_process.poll() is None:
        live_process.terminate()
        live_process = None
        return jsonify({"message": "Livebild gestoppt."})
    else:
        return jsonify({"message": "Kein Livebild aktiv."})

@app.route('/capture_image', methods=['POST'])
def capture_image():
    data = request.get_json()
    gain = float(data.get('gain', 10))
    exposure = float(data.get('exposure', 0.2))
    name = data.get('name', 'default')
    count = int(data.get('count', 1))

    os.makedirs(CAPTURE_DIR, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    for i in range(count):
        base_name = f"{timestamp}_Gain{gain}_Exp{exposure}_{name}"
        if count > 1:
            base_name += f"_{i+1}"

        dng_path = os.path.join(CAPTURE_DIR, base_name + ".dng")
        jpg_path = os.path.join(CAPTURE_DIR, base_name + ".jpg")
        ppm_path = os.path.join(CAPTURE_DIR, base_name + ".ppm")

        safe_gain = min(gain, 16)
        exposure_us = max(1000, int(exposure * 1_000_000))

        cmd = [
            "libcamera-still",
            "--shutter", str(exposure_us),
            "--gain", str(safe_gain),
            "--width", "4056",
            "--height", "3040",
            "--raw",         # wichtig: speichert .dng
            "-o", dng_path
        ]

        if exposure > 2.0:
            cmd += ["--awbgains", "1,1"]

        # Bild aufnehmen
        try:
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            return jsonify({"message": f"Fehler bei der Aufnahme: {e}"}), 500

        # Konvertiere DNG → PPM → JPG
        try:
            # dcraw erzeugt TIFF oder PPM
            with open(ppm_path, 'wb') as ppm_file:
                subprocess.run(
                    ["dcraw", "-4", "-c", "-W", "-o", "0", dng_path],
                    stdout=ppm_file,
                    check=True
                )

            image = cv2.imread(ppm_path, cv2.IMREAD_UNCHANGED)
            if image is None:
                raise Exception("PPM konnte nicht gelesen werden")

            resized = cv2.resize(image, (640, 480))
            cv2.imwrite(jpg_path, resized)
            os.remove(ppm_path)

        except Exception as e:
            return jsonify({"message": f"JPG-Konvertierung fehlgeschlagen: {e}"}), 500

    return jsonify({"message": f"{count} Bild(er) als DNG (4056x3040) + JPG (640x480) gespeichert."})


@app.route('/latest_image')
def latest_image():
    patterns = ["*.jpg", "*.jpeg", "*.JPG", "*.JPEG"]
    files = []
    for pattern in patterns:
        files.extend(glob.glob(os.path.join(CAPTURE_DIR, pattern)))

    files = sorted(files, key=os.path.getmtime, reverse=True)

    if not files:
        print("⚠️ Kein Bild gefunden in:", CAPTURE_DIR)
        abort(404, description="Kein Bild gefunden.")

    print("✅ Sende Bild:", files[0])
    return send_file(files[0], mimetype='image/jpeg')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
