"""
SafeWatch - Harassment Detection System
Hackathon Project | Offline-capable Flask Web App
"""

from flask import Flask, render_template, request, jsonify, send_from_directory, Response
import os, json, cv2, numpy as np, base64
from datetime import datetime
from pathlib import Path
import threading, time

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['INCIDENTS_FILE'] = 'incidents/incidents.json'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB

# Ensure directories exist
for d in ['uploads', 'incidents', 'models', 'static/css', 'static/js', 'templates']:
    os.makedirs(d, exist_ok=True)

# Global state
detection_status = {'running': False, 'progress': 0, 'result': None, 'frame': None}


# ─── Incident DB ────────────────────────────────────────────────────────────

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


# ─── Routes ─────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/incidents')
def incidents_page():
    return render_template('incidents.html')

@app.route('/train')
def train_page():
    return render_template('train.html')


# ─── API: Detection ──────────────────────────────────────────────────────────

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

    # Run detection in background thread
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


# ─── Detection Engine ────────────────────────────────────────────────────────

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
            
            # Process every 5th frame for speed
            if frame_count % 5 != 0:
                continue
            
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.resize(gray, (320, 240))
            score = 0.0
            
            if prev_gray is not None:
                # Optical flow - measures sudden/erratic movement
                flow = cv2.calcOpticalFlowFarneback(
                    prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
                )
                magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                mean_mag = np.mean(magnitude)
                max_mag = np.max(magnitude)
                std_mag = np.std(magnitude)
                
                # Erratic motion score (high variance = suspicious)
                motion_score = min(mean_mag * 2, 1.0)
                erratic_score = min(std_mag / (mean_mag + 1e-5) * 0.3, 1.0)
                
                # Detect rapid changes / sudden movements
                sudden_score = min(max_mag / 20.0, 1.0)
                
                # Proximity detection using dense optical flow zones
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
                
                # Edge detection for posture analysis
                edges = cv2.Canny(gray, 50, 150)
                edge_density = np.sum(edges > 0) / edges.size
                score += min(edge_density * 2, 0.2)
                score = min(score, 1.0)
                
                harassment_scores.append(score)
                
                # Save high-score frames as evidence
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
        
        # Final verdict
        if harassment_scores:
            avg_score = np.mean(harassment_scores)
            max_score = np.max(harassment_scores)
            high_frames = sum(1 for s in harassment_scores if s > 0.5)
            high_ratio = high_frames / len(harassment_scores)
            
            # Composite confidence
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
        
        # Auto-log incident if harassment detected
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


# ─── Training Engine ─────────────────────────────────────────────────────────

def run_training():
    """Train model on dataset/normal and dataset/harassment folders."""
    status_file = 'models/train_status.json'
    
    def update_status(msg, progress, done=False, accuracy=None):
        s = {'status': msg, 'progress': progress, 'done': done}
        if accuracy:
            s['accuracy'] = accuracy
        with open(status_file, 'w') as f:
            json.dump(s, f)
    
    try:
        update_status('Scanning dataset folders...', 5)
        
        normal_dir = 'dataset/normal'
        harass_dir = 'dataset/harassment'
        
        normal_files = list(Path(normal_dir).glob('*.mp4')) if os.path.exists(normal_dir) else []
        harass_files = list(Path(harass_dir).glob('*.mp4')) if os.path.exists(harass_dir) else []
        
        if not normal_files and not harass_files:
            update_status(f'No MP4 files found in dataset/normal or dataset/harassment. Add videos and retry.', 0, done=True)
            return
        
        total = len(normal_files) + len(harass_files)
        update_status(f'Found {len(normal_files)} normal, {len(harass_files)} harassment videos', 10)
        
        features, labels = [], []
        processed = 0
        
        def extract_features(video_path):
            """Extract motion features from video."""
            cap = cv2.VideoCapture(str(video_path))
            flow_magnitudes, flow_stds = [], []
            prev_gray = None
            frame_count = 0
            
            while cap.isOpened() and frame_count < 150:
                ret, frame = cap.read()
                if not ret:
                    break
                frame_count += 1
                if frame_count % 3 != 0:
                    continue
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                gray = cv2.resize(gray, (160, 120))
                if prev_gray is not None:
                    flow = cv2.calcOpticalFlowFarneback(
                        prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
                    )
                    mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                    flow_magnitudes.append(np.mean(mag))
                    flow_stds.append(np.std(mag))
                prev_gray = gray.copy()
            cap.release()
            
            if not flow_magnitudes:
                return None
            return [
                np.mean(flow_magnitudes),
                np.std(flow_magnitudes),
                np.max(flow_magnitudes),
                np.mean(flow_stds),
                np.percentile(flow_magnitudes, 75),
                np.percentile(flow_magnitudes, 90)
            ]
        
        for vpath in normal_files:
            update_status(f'Processing: {vpath.name}', 10 + int(processed/total*70))
            feat = extract_features(vpath)
            if feat:
                features.append(feat)
                labels.append(0)
            processed += 1
        
        for vpath in harass_files:
            update_status(f'Processing: {vpath.name}', 10 + int(processed/total*70))
            feat = extract_features(vpath)
            if feat:
                features.append(feat)
                labels.append(1)
            processed += 1
        
        update_status('Training classifier...', 82)
        
        if len(features) < 2:
            update_status('Need at least 2 labeled videos to train', 0, done=True)
            return
        
        X = np.array(features)
        y = np.array(labels)
        
        # Normalize
        X_mean = X.mean(axis=0)
        X_std = X.std(axis=0) + 1e-8
        X_norm = (X - X_mean) / X_std
        
        # Simple threshold-based classifier (no sklearn needed)
        # Find best threshold per feature using labeled data
        thresholds = {}
        for i in range(X_norm.shape[1]):
            normal_vals = X_norm[y==0, i] if np.any(y==0) else np.array([0])
            harass_vals = X_norm[y==1, i] if np.any(y==1) else np.array([0])
            thresholds[f'feat_{i}'] = {
                'normal_mean': float(np.mean(normal_vals)),
                'harass_mean': float(np.mean(harass_vals)),
                'threshold': float((np.mean(normal_vals) + np.mean(harass_vals)) / 2)
            }
        
        # Save model as JSON
        model_data = {
            'X_mean': X_mean.tolist(),
            'X_std': X_std.tolist(),
            'thresholds': thresholds,
            'n_normal': int(np.sum(y==0)),
            'n_harassment': int(np.sum(y==1)),
            'trained_at': datetime.now().isoformat()
        }
        with open('models/model.json', 'w') as f:
            json.dump(model_data, f, indent=2)
        
        # Compute accuracy
        correct = 0
        for i in range(len(X_norm)):
            vote = sum(
                1 if X_norm[i, int(k.split('_')[1])] > v['threshold'] else 0
                for k, v in thresholds.items()
            )
            pred = 1 if vote > len(thresholds) / 2 else 0
            if pred == y[i]:
                correct += 1
        accuracy = round(correct / len(y) * 100, 1)
        
        update_status(f'Training complete! Accuracy: {accuracy}%', 100, done=True, accuracy=accuracy)
    
    except Exception as e:
        with open(status_file, 'w') as f:
            json.dump({'status': f'Error: {str(e)}', 'progress': 0, 'done': True}, f)


if __name__ == '__main__':
    print("\n" + "="*50)
    print("  SafeWatch - Harassment Detection System")
    print("  Running at: http://127.0.0.1:5000")
    print("="*50 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
