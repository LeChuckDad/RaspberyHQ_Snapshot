from flask import Flask, render_template, Response, jsonify, request
from picamera2 import Picamera2
import threading
import cv2
import time
import os

app = Flask(__name__)
picam2 = Picamera2()
video_config = picam2.create_video_configuration(main={"size": (640, 480)})
# Konfiguration für RAW und JPEG
config = picam2.create_still_configuration(main={"size": (640, 480)}, raw={"size": (6112, 3040)})
#config = picam2.create_still_configuration(main={"size": (640, 480)}, raw={"size": (6112, 3040), "format": "Bayer"})
picam2.configure(config)
lock = threading.Lock()

camera_running = False

# Definiere den minimalen Wert für die Belichtungszeit (in Sekunden)
MIN_EXPOSURE_TIME = 0.01  # 10 ms

# Funktion zur Konfiguration der Kamera mit Gain und Belichtungszeit (Auto-Exposure deaktivieren)
def configure_camera(gain, exposure):
    # Überprüfe, ob die Belichtungszeit kleiner als der minimal mögliche Wert ist
    exposure = max(exposure, MIN_EXPOSURE_TIME)
    
    controls = {
        "AnalogueGain": float(gain),
        "ExposureTime": int(exposure * 1_000_000),  # Belichtungszeit in Mikrosekunden
        # Entferne die Zeile mit ExposureMode, da sie nicht unterstützt wird
        # "ExposureMode": "off"  # Auto-Exposure deaktivieren
    }
    picam2.set_controls(controls)

def start_camera():
    global camera_running
    with lock:
        if not camera_running:
            picam2.configure(video_config)
            camera_running = True
            picam2.start()

def stop_camera():
    global camera_running
    with lock:
        if camera_running:
            picam2.stop()
            camera_running = False

def gen_frames():
    while True:
        with lock:
            if not camera_running:
                break
            frame = picam2.capture_array()
        _, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    with lock:
        if not camera_running:
            return "Kamera läuft nicht", 503
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/toggle_camera', methods=['POST'])
def toggle_camera():
    global camera_running
    if camera_running:
        stop_camera()
    else:
        start_camera()
    return jsonify({"running": camera_running})

@app.route('/capture_image', methods=['POST'])
def capture_image():
    data = request.get_json()
    gain = data.get('gain', 80)
    exposure = data.get('exposure', 0.2)
    name = data.get('name', 'Test')
    count = data.get('count', 1)

    was_running = camera_running
    if camera_running:
        stop_camera()

    # Konfiguration für RAW und JPEG
    config = picam2.create_still_configuration(main={"size": (640, 480)}, raw={"size": (6112, 3040)})
    #config = picam2.create_still_configuration(main={"size": (640, 480)}, raw={"size": (6112, 3040), "format": "Bayer"})
    picam2.configure(config)

    # Setze die Gain- und Belichtungszeit für die Kamera und deaktiviere Auto-Exposure
    configure_camera(gain, exposure)
    
    picam2.start()
    time.sleep(0.5)

    os.makedirs("captures", exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")

    for i in range(count):
        base_name = f"{timestamp}_Gain{gain}_Exp{exposure}_{name}"
        if count > 1:
            base_name += f"_{i+1}"

        # Capture RAW und als .raw speichern
        raw_data = picam2.capture_array("raw")
#        jpg_data = picam2.capture_array("jpg")
        raw_data = raw_data.reshape((3040, 6112))  # RAW-Daten auf die richtige Auflösung umwandeln

        # RAW-Daten als .raw-Datei speichern
        raw_path = f"captures/{base_name}.raw"
        raw_data.tofile(raw_path)
 #       jpg_path = f"captures/{base_name}.jpgw"
  #      jpg_data.tofile(jpg_path)

        # Umwandlung der RAW-Daten in JPEG mit 640x480 Auflösung
        raw_image = cv2.cvtColor(raw_data, cv2.COLOR_BayerBG2BGR)  # Umwandlung von RAW zu BGR
        raw_image_resized = cv2.resize(raw_image, (640, 480))  # Skalierung auf 640x480
        raw_jpeg_path = f"captures/{base_name}_raw_to_jpeg.jpg"
        cv2.imwrite(raw_jpeg_path, raw_image_resized)

    picam2.stop()

    if was_running:
        start_camera()

    return jsonify({"message": f"{count} Bild(er) als RAW + JPEG gespeichert."})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
