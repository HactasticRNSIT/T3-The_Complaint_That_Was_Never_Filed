# SafeWatch — Harassment Detection + Emergency SOS
### Fully Integrated Project | Python + Flask

---

## ⚡ Quick Start (3 steps)

### 1. Place your siren.mp3
Copy your `siren.mp3` file into the `static/` folder:
```
safewatch/static/siren.mp3
```

### 2. Set your emergency contact number
Open `app.py` and find this line (around line 58):
```python
phone = "91XXXXXXXXXX"
```
Replace with the real number. Format: country code + number, no spaces or +
Example: `"919876543210"` for an Indian number.

### 3. Install & Run
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run
python app.py
```

Then open: **http://127.0.0.1:5000**

---

## 📁 Project Structure
```
safewatch/
├── app.py                    ← Main server (all routes integrated)
├── requirements.txt
├── generate_demo_data.py     ← Populate sample incidents for demo
├── templates/
│   ├── index.html            ← Harassment video upload & analysis
│   ├── dashboard.html        ← Stats & charts
│   ├── incidents.html        ← Incident registry
│   ├── train.html            ← Model training UI
│   └── sos.html              ← Emergency SOS button page
├── static/
│   └── siren.mp3             ← ⚠️ YOU MUST ADD THIS FILE
├── dataset/
│   ├── normal/               ← Add normal .mp4 videos here for training
│   └── harassment/           ← Add harassment .mp4 videos here for training
├── uploads/                  ← Analyzed videos stored here (auto-created)
├── incidents/                ← incidents.json database (auto-created)
└── models/                   ← Trained model saved here (auto-created)
```

---

## 🌐 Pages

| URL | Page |
|-----|------|
| http://127.0.0.1:5000/ | Upload & analyze CCTV footage |
| http://127.0.0.1:5000/dashboard | Live stats & charts |
| http://127.0.0.1:5000/incidents | Incident registry |
| http://127.0.0.1:5000/train | Train model on your dataset |
| http://127.0.0.1:5000/sos | **Emergency SOS button** |

---

## 🆘 How SOS Works
1. Open http://127.0.0.1:5000/sos
2. Press the red SOS button
3. Browser asks for location permission — click **Allow**
4. Siren plays, GPS coordinates are captured
5. WhatsApp opens with a pre-filled emergency message + Google Maps link
6. Send the message to alert your emergency contact

---

## 📊 Demo Data
Run this to populate 20 sample incidents before your demo:
```bash
python generate_demo_data.py
```
