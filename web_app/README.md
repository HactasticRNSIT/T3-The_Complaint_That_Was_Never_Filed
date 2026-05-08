# SafeWatch — Harassment Detection System
### Hackathon Project | Python + Flask | Offline-Capable

---

## 🚀 Quick Start (VS Code)

### 1. Install Dependencies
```bash
pip install flask opencv-python numpy
```

### 2. Add Your Dataset
```
harassment_detection/
├── dataset/
│   ├── normal/        ← Copy your NORMAL .mp4 files here
│   └── harassment/    ← Copy your HARASSMENT .mp4 files here
```

### 3. Generate Demo Data (optional)
```bash
python generate_demo_data.py
```

### 4. Run the App
```bash
python app.py
```

### 5. Open Browser
```
http://127.0.0.1:5000
```

---

## 📁 Project Structure
```
harassment_detection/
├── app.py                  ← Main Flask server + detection engine
├── requirements.txt        ← Python dependencies
├── generate_demo_data.py   ← Populate demo incidents
├── templates/
│   ├── index.html          ← Upload & analyze page
│   ├── dashboard.html      ← Stats & charts
│   ├── incidents.html      ← Incident registry
│   └── train.html          ← Model training UI
├── dataset/
│   ├── normal/             ← Your normal videos here
│   └── harassment/         ← Your harassment videos here
├── uploads/                ← Analyzed videos stored here
├── incidents/              ← incidents.json database
└── models/                 ← Trained model saved here
```

---

## 🧠 How It Works

### Detection Pipeline
1. **Upload** CCTV footage via drag & drop
2. **Optical Flow** (Farneback algorithm) tracks motion between frames
3. **Feature Scoring** — 4 components:
   - Motion magnitude (erratic = suspicious)
   - Flow variance (high std = aggressive movement)
   - Sudden burst detection (max flow spike)
   - Center-zone activity (proximity behavior)
4. **Verdict** returned: HARASSMENT_DETECTED / SUSPICIOUS / NORMAL
5. **Evidence frames** extracted at high-score timestamps
6. **Auto-logged** to incident registry if threat detected

### Training Pipeline
1. Place videos in `dataset/normal/` and `dataset/harassment/`
2. Click "Start Training" in the UI
3. System extracts 6 motion features per video
4. Threshold classifier trained, saved to `models/model.json`
5. Accuracy displayed after training

---

## 🌐 Pages
| URL | Page |
|-----|------|
| `/` | Upload & Analyze footage |
| `/dashboard` | Live stats, charts, severity breakdown |
| `/incidents` | Full incident registry, filter, export CSV |
| `/train` | Train model on your dataset |

---

## ⚡ Offline Mode
- No internet required after setup
- All processing is local (CPU)
- Data stored in `incidents/incidents.json`
- No cloud dependencies

---

## 🛠 Tech Stack
- **Python 3.8+**
- **Flask** — Web server
- **OpenCV** — Video processing & optical flow
- **NumPy** — Feature computation
- No PyTorch / TensorFlow needed!

---

## 📊 Demo
Run `python generate_demo_data.py` to populate 20 realistic sample incidents before your demo.

---

*Built for Hackathon — SafeWatch v1.0*
