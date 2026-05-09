"""
SafeWatch - Harassment Detection + SOS + Login/Register
========================================================
Role Access:
  USER  -> Analysis (/), SOS (/sos)
  ADMIN -> Analysis (/), System Dashboard (/dashboard), Incidents (/incidents), Train (/train)

Default Accounts (created on first run):
  admin / admin123
  user  / user123
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_cors import CORS
import os, json, cv2, numpy as np, base64, hashlib, secrets
from datetime import datetime
from pathlib import Path
import threading
from urllib.parse import quote
from functools import wraps

app = Flask(__name__)
app.secret_key = 'safewatch-secret-key-change-in-production'
CORS(app)

UPLOAD_FOLDER   = 'uploads'
INCIDENTS_FILE  = 'incidents/incidents.json'
USERS_FILE      = 'incidents/users.json'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

for d in ['uploads','incidents','models','static','dataset/normal','dataset/harassment']:
    os.makedirs(d, exist_ok=True)

detection_status = {'running': False, 'progress': 0, 'result': None}


# ── Helpers ───────────────────────────────────────────────────────────────────

def hp(pw): return hashlib.sha256(pw.encode()).hexdigest()

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE) as f: return json.load(f)
    defaults = [
        {'username':'admin','password':hp('admin123'),'role':'admin','name':'Administrator'},
        {'username':'user', 'password':hp('user123'), 'role':'user', 'name':'User'}
    ]
    with open(USERS_FILE,'w') as f: json.dump(defaults,f,indent=2)
    return defaults

def save_users(u):
    with open(USERS_FILE,'w') as f: json.dump(u,f,indent=2)

def get_user(username):
    return next((u for u in load_users() if u['username']==username), None)

def load_incidents():
    if os.path.exists(INCIDENTS_FILE):
        with open(INCIDENTS_FILE) as f: return json.load(f)
    return []

def save_incident(inc):
    incs = load_incidents(); incs.append(inc)
    with open(INCIDENTS_FILE,'w') as f: json.dump(incs,f,indent=2)


# ── Decorators ────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def dec(*a,**k):
        if 'username' not in session: return redirect(url_for('login_page'))
        return f(*a,**k)
    return dec

def admin_required(f):
    @wraps(f)
    def dec(*a,**k):
        if 'username' not in session: return redirect(url_for('login_page'))
        if session.get('role') != 'admin':
            return render_template('denied.html', username=session.get('name',''), role=session.get('role',''))
        return f(*a,**k)
    return dec


# ── Auth Routes ───────────────────────────────────────────────────────────────
@app.route('/safety-map')
def safety_map():
    """Renders the map view."""
    return render_template('map_view.html')

@app.route('/login', methods=['GET'])
def login_page():
    if 'username' in session: return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login_post():
    d = request.json
    u = get_user(d.get('username','').strip())
    if u and u['password'] == hp(d.get('password','')):
        session.update({'username':u['username'],'role':u['role'],'name':u['name']})
        return jsonify({'success':True,'role':u['role'],'name':u['name']})
    return jsonify({'success':False,'error':'Invalid username or password'}), 401

@app.route('/register', methods=['GET'])
def register_page():
    if 'username' in session: return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/register', methods=['POST'])
def register_post():
    d = request.json
    username = d.get('username','').strip()
    password = d.get('password','')
    name     = d.get('name','').strip()
    if not username or not password or not name:
        return jsonify({'success':False,'error':'All fields are required'}), 400
    if len(username) < 3:
        return jsonify({'success':False,'error':'Username must be at least 3 characters'}), 400
    if len(password) < 6:
        return jsonify({'success':False,'error':'Password must be at least 6 characters'}), 400
    users = load_users()
    if any(u['username']==username for u in users):
        return jsonify({'success':False,'error':'Username already taken'}), 400
    nu = {'username':username,'password':hp(password),'role':'user','name':name}
    users.append(nu); save_users(users)
    session.update({'username':username,'role':'user','name':name})
    return jsonify({'success':True,'role':'user','name':name})

@app.route('/logout')
def logout():
    session.clear(); return redirect(url_for('login_page'))

@app.route('/api/me')
def api_me():
    if 'username' not in session: return jsonify({'logged_in':False}), 401
    return jsonify({'logged_in':True,'username':session['username'],'role':session['role'],'name':session['name']})


# ── Page Routes ───────────────────────────────────────────────────────────────

@app.route('/')
@login_required
def index():
    return render_template('index.html', username=session['name'], role=session['role'])

@app.route('/dashboard')
@admin_required
def dashboard():
    return render_template('dashboard.html', username=session['name'], role=session['role'])

@app.route('/incidents')
@admin_required
def incidents_page():
    return render_template('incidents.html', username=session['name'], role=session['role'])


@app.route('/sos')
@login_required
def sos_page():
    return render_template('sos.html', username=session['name'], role=session['role'])


# ── SOS ───────────────────────────────────────────────────────────────────────

@app.route('/send_sos', methods=['POST'])
@login_required
def send_sos():
    data = request.json
    location   = data.get('location','Unknown')
    by         = session.get('name','Unknown User')
    # ⚠️  Replace with real emergency contact — format: countrycode+number no spaces
    # Example India: "919876543210"
    phone      = "91XXXXXXXXXX"
    message    = quote(f"🚨 EMERGENCY ALERT!\nTriggered by: {by}\nLocation: {location}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    link       = f"https://wa.me/{phone}?text={message}"
    print(f"SOS by {by} → {link}")
    return jsonify({'whatsapp_link': link})


# ── API ───────────────────────────────────────────────────────────────────────

@app.route('/api/analyze', methods=['POST'])
@login_required
def analyze_video():
    if 'video' not in request.files: return jsonify({'error':'No video'}), 400
    f = request.files['video']
    if not f.filename: return jsonify({'error':'Empty filename'}), 400
    fn = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{f.filename}"
    fp = os.path.join(UPLOAD_FOLDER, fn); f.save(fp)
    detection_status.update({'running':True,'progress':0,'result':None})
    t = threading.Thread(target=run_detection, args=(fp,fn)); t.daemon=True; t.start()
    return jsonify({'status':'started','filename':fn})

@app.route('/api/detection_status')
@login_required
def get_detection_status(): return jsonify(detection_status)

@app.route('/api/incidents', methods=['GET'])
@login_required
def get_incidents(): return jsonify(load_incidents())

@app.route('/api/incidents', methods=['POST'])
@login_required
def add_incident():
    d = request.json
    inc = {
        'id':f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        'timestamp':datetime.now().isoformat(),
        'type':d.get('type','Manual Report'),
        'location':d.get('location','Unknown'),
        'description':d.get('description',''),
        'severity':d.get('severity','medium'),
        'status':'Open','source':d.get('source','manual'),
        'confidence':d.get('confidence',None),
        'video_file':d.get('video_file',None),
        'evidence_frames':d.get('evidence_frames',[]),
        'reported_by':session.get('name','Unknown')
    }
    save_incident(inc); return jsonify(inc)

@app.route('/api/incidents/<iid>/status', methods=['PUT'])
@admin_required
def update_incident_status(iid):
    d = request.json; incs = load_incidents()
    for i in incs:
        if i['id']==iid: i['status']=d.get('status',i['status']); break
    with open(INCIDENTS_FILE,'w') as f: json.dump(incs,f,indent=2)
    return jsonify({'success':True})

@app.route('/api/stats')
@login_required
def get_stats():
    incs = load_incidents()
    sev = {'high':0,'medium':0,'low':0}
    for i in incs:
        s = i.get('severity','medium').lower()
        if s in sev: sev[s]+=1
    return jsonify({'total':len(incs),'open':sum(1 for i in incs if i.get('status')=='Open'),
                    'resolved':sum(1 for i in incs if i.get('status')=='Resolved'),
                    'ai_detected':sum(1 for i in incs if i.get('source')=='ai'),'severity':sev})

@app.route('/api/train', methods=['POST'])
@admin_required
def train_model():
    t=threading.Thread(target=run_training); t.daemon=True; t.start()
    return jsonify({'status':'training_started'})

@app.route('/api/train_status')
@login_required
def train_status():
    sf='models/train_status.json'
    if os.path.exists(sf):
        with open(sf) as f: return jsonify(json.load(f))
    return jsonify({'status':'idle','progress':0})


# ── Detection Engine ──────────────────────────────────────────────────────────

def run_detection(filepath, filename):
    global detection_status
    try:
        cap = cv2.VideoCapture(filepath)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps   = cap.get(cv2.CAP_PROP_FPS) or 30
        scores, evidence, fc, pg = [], [], 0, None
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret: break
            fc += 1
            detection_status['progress'] = min(int(fc/max(total,1)*100), 99)
            if fc % 5 != 0: continue
            gray = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (320,240))
            if pg is not None:
                flow = cv2.calcOpticalFlowFarneback(pg, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
                mag, _ = cv2.cartToPolar(flow[...,0], flow[...,1])
                mm = np.mean(mag)
                score = min(
                    mm*2*0.25 + min(np.std(mag)/(mm+1e-5)*0.3,1)*0.30 +
                    min(np.max(mag)/20,1)*0.20 + min(np.mean(mag[60:180,80:240])*3,1)*0.25 +
                    min(np.sum(cv2.Canny(gray,50,150)>0)/gray.size*2,0.2), 1.0)
                scores.append(score)
                if score > 0.6 and len(evidence) < 5:
                    ts = fc/fps
                    _, buf = cv2.imencode('.jpg', cv2.resize(frame,(320,180)))
                    evidence.append({'timestamp':f"{int(ts//60):02d}:{int(ts%60):02d}",
                                     'score':round(score,3),
                                     'frame':f"data:image/jpeg;base64,{base64.b64encode(buf).decode()}"})
            pg = gray.copy()
        cap.release()
        if scores:
            avg,mx,hr = np.mean(scores),np.max(scores),sum(1 for s in scores if s>0.5)/len(scores)
            conf = min(avg*0.4+mx*0.3+hr*0.3,1.0)
            if conf>0.55: verdict,sev = 'HARASSMENT_DETECTED',('high' if conf>0.75 else 'medium')
            elif conf>0.35: verdict,sev = 'SUSPICIOUS','medium'
            else: verdict,sev = 'NORMAL','low'
        else: conf,verdict,sev = 0.0,'NORMAL','low'
        result = {'verdict':verdict,'confidence':round(float(conf),3),'severity':sev,
                  'frames_analyzed':fc,'evidence_frames':evidence,'filename':filename,
                  'timestamp':datetime.now().isoformat()}
        detection_status.update({'result':result,'running':False,'progress':100})
        if verdict in ['HARASSMENT_DETECTED','SUSPICIOUS']:
            save_incident({'id':f"INC-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                           'timestamp':datetime.now().isoformat(),
                           'type':'AI Detected - '+verdict.replace('_',' ').title(),
                           'location':'CCTV Camera',
                           'description':f"AI detected {verdict.replace('_',' ').lower()} in {filename}. Confidence: {round(conf*100,1)}%",
                           'severity':sev,'status':'Open','source':'ai',
                           'confidence':round(float(conf),3),'video_file':filename,
                           'evidence_frames':[e['timestamp'] for e in evidence],
                           'reported_by':'AI System'})
    except Exception as e:
        detection_status.update({'running':False,'result':{'error':str(e),'verdict':'ERROR'},'progress':0})


if __name__=='__main__':
    load_users()
    print("\n"+"="*55)
    print("  SafeWatch — Harassment Detection + SOS + Auth")
    print("  URL:    http://127.0.0.1:5000")
    print("  Admin:  username=admin  password=admin123")
    print("  User:   username=user   password=user123")
    print("="*55+"\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
