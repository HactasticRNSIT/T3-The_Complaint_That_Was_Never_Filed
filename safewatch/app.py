"""
SafeWatch - Harassment Detection System + Emergency SOS
Hackathon Project | Offline-capable Flask Web App
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from flask_cors import CORS
import os, json, cv2, numpy as np, base64
from datetime import datetime
from pathlib import Path
import threading, time
from urllib.parse import quote

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['INCIDENTS_FILE'] = 'incidents/incidents.json'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

# Ensure directories exist
for d in ['uploads', 'incidents', 'models', 'static', 'templates',
          'dataset/normal', 'dataset/harassment']:
    os.makedirs(d, exist_ok=True)

# Global state
detection_status = {'running': False, 'progress': 0, 'result': None, 'frame': None}


# ─── Incident DB ─────────────────────────────────────────────────────────────

def load_incidents():
    if os.path.exists(app.config['INCIDENTS_FILE']):
        with open(app.config['INCIDENTS_FILE']) as f:
            return json.load(f)
    return []

def save_incident(incident):
    incidents = load_incidents()
    incidents.append(incident)
    with open(app.config['INCIDENTS_FILE'], 'w') as f:
        json.dump(incidents, f, indent=2)
    return incident


# ─── Page Routes ─────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/incidents')
def incidents_page():
    return render_template('incidents.html')

@app.route('/sos')
def sos_page():
    return render_template('sos.html')


# ─── SOS Emergency Route ──────────────────────────────────────────────────────

@app.route('/send_sos', methods=['POST'])
def send_sos():
    data = request.json
    location = data.get('location', 'Unknown')

    # ⚠️ IMPORTANT: Replace with the real emergency contact number
    # Format: country code + number, no +, spaces, or dashes
    # Example for India: "919876543210"
    phone = "91XXXXXXXXXX"

    message = quote(f"🚨 EMERGENCY ALERT! I need help. My location: {location}")
    whatsapp_link = f"https://wa.me/{phone}?text={message}"

    print("SOS TRIGGERED — WhatsApp Link:", whatsapp_link)
    return jsonify({"whatsapp_link": whatsapp_link})


# ─── API: Detection ───────────────────────────────────────────────────────────

@app.route('/api/analyze', methods=['POST'])
def analyze_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video uploaded'}), 400

    file = request.files['video']
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400

    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file.filename}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    detection_status['running'] = True
    detection_status['progress'] = 0
    detection_status['result'] = None

    thread = threading.Thread(target=run_detection, args=(filepath, filename))
    thread.daemon = True
    thread.start()

    return jsonify({'status': 'started', 'filename': filename})


@app.route('/api/detection_status')
def get_detection_status():
    return jsonify(detection_status)


@app.route('/api/incidents', methods=['GET'])
def get_incidents():
    return jsonify(load_incidents())


@app.route('/api/incidents', methods=['POST'])
def add_incident():
    data = request.json
    incident = {
        'id': f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'timestamp': datetime.now().isoformat(),
        'type': data.get('type', 'Manual Report'),
        'location': data.get('location', 'Unknown'),
        'description': data.get('description', ''),
        'severity': data.get('severity', 'medium'),
        'status': 'Open',
        'source': data.get('source', 'manual'),
        'confidence': data.get('confidence', None),
        'video_file': data.get('video_file', None),
        'evidence_frames': data.get('evidence_frames', [])
    }
    save_incident(incident)
    return jsonify(incident)


@app.route('/api/incidents/<inc_id>/status', methods=['PUT'])
def update_incident_status(inc_id):
    data = request.json
    incidents = load_incidents()
    for inc in incidents:
        if inc['id'] == inc_id:
            inc['status'] = data.get('status', inc['status'])
            break
    with open(app.config['INCIDENTS_FILE'], 'w') as f:
        json.dump(incidents, f, indent=2)
    return jsonify({'success': True})


@app.route('/api/stats')
def get_stats():
    incidents = load_incidents()
    total = len(incidents)
    open_count = sum(1 for i in incidents if i.get('status') == 'Open')
    resolved = sum(1 for i in incidents if i.get('status') == 'Resolved')
    ai_detected = sum(1 for i in incidents if i.get('source') == 'ai')
    severity_counts = {'high': 0, 'medium': 0, 'low': 0}
    for inc in incidents:
        sev = inc.get('severity', 'medium').lower()
        if sev in severity_counts:
            severity_counts[sev] += 1
    return jsonify({
        'total': total,
        'open': open_count,
        'resolved': resolved,
        'ai_detected': ai_detected,
        'severity': severity_counts
    })


@app.route('/api/train', methods=['POST'])
def train_model():
    thread = threading.Thread(target=run_training)
    thread.daemon = True
    thread.start()
    return jsonify({'status': 'training_started'})


@app.route('/api/train_status')
def train_status():
    status_file = 'models/train_status.json'
    if os.path.exists(status_file):
        with open(status_file) as f:
            return jsonify(json.load(f))
    return jsonify({'status': 'idle', 'progress': 0})


# ─── Detection Engine ─────────────────────────────────────────────────────────

def run_detection(filepath, filename):
    """Core harassment detection using optical flow + motion analysis."""
    global detection_status
    try:
        cap = cv2.VideoCapture(filepath)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS) or 30

        harassment_scores = []
        evidence_frames = []
        frame_count = 0
        prev_gray = None

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1
            progress = int((frame_count / max(total_frames, 1)) * 100)
            detection_status['progress'] = min(progress, 99)

            if frame_count % 5 != 0:
                continue

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (320, 240))
            score = 0.0

            if prev_gray is not None:
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
                )
                magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                mean_mag = np.mean(magnitude)
                max_mag = np.max(magnitude)
                std_mag = np.std(magnitude)

                motion_score = min(mean_mag * 2, 1.0)
                erratic_score = min(std_mag / (mean_mag + 1e-5) * 0.3, 1.0)
                sudden_score = min(max_mag / 20.0, 1.0)

                h, w = magnitude.shape
                center_zone = magnitude[h//4:3*h//4, w//4:3*w//4]
                center_activity = np.mean(center_zone)
                proximity_score = min(center_activity * 3, 1.0)

                score = (
                    motion_score * 0.25 +
                    erratic_score * 0.30 +
                    sudden_score * 0.20 +
                    proximity_score * 0.25
                )

                edges = cv2.Canny(gray, 50, 150)
                edge_density = np.sum(edges > 0) / edges.size
                score += min(edge_density * 2, 0.2)
                score = min(score, 1.0)

                harassment_scores.append(score)

                if score > 0.6 and len(evidence_frames) < 5:
                    timestamp_sec = frame_count / fps
                    _, buf = cv2.imencode('.jpg', cv2.resize(frame, (320, 180)))
                    b64 = base64.b64encode(buf).decode('utf-8')
                    evidence_frames.append({
                        'timestamp': f"{int(timestamp_sec//60):02d}:{int(timestamp_sec%60):02d}",
                        'score': round(score, 3),
                        'frame': f"data:image/jpeg;base64,{b64}"
                    })

            prev_gray = gray.copy()

        cap.release()

        if harassment_scores:
            avg_score = np.mean(harassment_scores)
            max_score = np.max(harassment_scores)
            high_frames = sum(1 for s in harassment_scores if s > 0.5)
            high_ratio = high_frames / len(harassment_scores)
            confidence = min((avg_score * 0.4 + max_score * 0.3 + high_ratio * 0.3), 1.0)

            if confidence > 0.55:
                verdict = 'HARASSMENT_DETECTED'
                severity = 'high' if confidence > 0.75 else 'medium'
            elif confidence > 0.35:
                verdict = 'SUSPICIOUS'
                severity = 'medium'
            else:
                verdict = 'NORMAL'
                severity = 'low'
        else:
            confidence = 0.0
            verdict = 'NORMAL'
            severity = 'low'

        result = {
            'verdict': verdict,
            'confidence': round(float(confidence), 3),
            'severity': severity,
            'frames_analyzed': frame_count,
            'evidence_frames': evidence_frames,
            'filename': filename,
            'timestamp': datetime.now().isoformat()
        }

        detection_status['result'] = result
        detection_status['running'] = False
        detection_status['progress'] = 100

        if verdict in ['HARASSMENT_DETECTED', 'SUSPICIOUS']:
            incident = {
                'id': f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'timestamp': datetime.now().isoformat(),
                'type': 'AI Detected - ' + verdict.replace('_', ' ').title(),
                'location': 'CCTV Camera',
                'description': f"AI detected {verdict.replace('_', ' ').lower()} in video {filename}. Confidence: {round(confidence*100, 1)}%",
                'severity': severity,
                'status': 'Open',
                'source': 'ai',
                'confidence': round(float(confidence), 3),
                'video_file': filename,
                'evidence_frames': [ef.get('timestamp') for ef in evidence_frames]
            }
            save_incident(incident)

    except Exception as e:
        detection_status['running'] = False
        detection_status['result'] = {'error': str(e), 'verdict': 'ERROR'}
        detection_status['progress'] = 0


if __name__ == '__main__':
    print("\n" + "="*55)
    print("  SafeWatch — Harassment Detection + Emergency SOS")
    print("  Running at: http://127.0.0.1:5000")
    print("  SOS Page:   http://127.0.0.1:5000/sos")
    print("="*55 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
