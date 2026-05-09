# SafeWatch v2.0 — Full Integrated Project
### Harassment Detection + Emergency SOS + Login/Register + Role-Based Access

---

## ⚡ Quick Start

### Step 1 — Add your siren.mp3
Copy siren.mp3 into the `static/` folder:
```
safewatch_full/static/siren.mp3
```

### Step 2 — Set your emergency WhatsApp number
Open `app.py`, find line with `phone = "91XXXXXXXXXX"` and replace:
```python
phone = "919876543210"   # Example: India number
```

### Step 3 — Setup & Run (Windows PowerShell)
```powershell
cd safewatch_full
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

### Step 4 — Open browser
```
http://127.0.0.1:5000
```

---

## 🔑 Default Login Accounts

| Username | Password | Role  | Access |
|----------|----------|-------|--------|
| admin    | admin123 | Admin | Analysis + Dashboard + Incidents + Train + SOS |
| user     | user123  | User  | Analysis + SOS only |

New registrations are always created as **User** role.

---

## 🌐 Pages & Access

| URL | Page | User | Admin |
|-----|------|------|-------|
| /login | Login page | ✅ | ✅ |
| /register | Register page | ✅ | ✅ |
| / | Analysis (upload CCTV) | ✅ | ✅ |
| /sos | Emergency SOS button | ✅ | ✅ |
| /dashboard | System Dashboard | ❌ | ✅ |
| /incidents | Incident Registry | ❌ | ✅ |
| /train | Train Model | ❌ | ✅ |

---

## 📁 Project Structure
```
safewatch_full/
├── app.py                  ← Main server (all routes + auth)
├── requirements.txt
├── templates/
│   ├── login.html          ← Login page
│   ├── register.html       ← Register page
│   ├── denied.html         ← Access denied page
│   ├── index.html          ← Analysis page (user + admin)
│   ├── sos.html            ← Emergency SOS (user + admin)
│   ├── dashboard.html      ← System Dashboard (admin only)
│   ├── incidents.html      ← Incidents (admin only)
│   └── train.html          ← Train Model (admin only)
├── static/
│   └── siren.mp3           ← ⚠️ YOU MUST ADD THIS FILE
├── dataset/
│   ├── normal/             ← Add normal .mp4 videos for training
│   └── harassment/         ← Add harassment .mp4 videos for training
├── uploads/                ← Auto-created: analyzed videos stored here
├── incidents/              ← Auto-created: incidents.json + users.json
└── models/                 ← Auto-created: trained model saved here
```

---

## 🆘 How SOS Works
1. Login as any user → go to `/sos`
2. Press the red SOS button
3. Browser asks for location permission → click Allow
4. Siren plays + GPS is captured
5. WhatsApp opens with pre-filled message + Google Maps link
6. Send it to alert your emergency contact

---

## ❓ Common Issues

**`venv\Scripts\activate` gives error** → Run first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

**Siren doesn't play** → Make sure `siren.mp3` is in the `static/` folder.

**Port 5000 already in use** → Change last line of app.py:
```python
app.run(debug=True, host='0.0.0.0', port=5001)
```
