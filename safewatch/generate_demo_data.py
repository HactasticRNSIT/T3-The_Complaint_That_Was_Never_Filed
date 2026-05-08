"""
generate_demo_data.py
Run this once to populate demo incidents for the hackathon demo.
Usage: python generate_demo_data.py
"""
import json, os, random
from datetime import datetime, timedelta

os.makedirs('incidents', exist_ok=True)

types = [
    "Physical Altercation", "Verbal Harassment", "Threatening Behavior",
    "AI: Harassment Detected", "AI: Suspicious Activity",
    "Stalking/Following", "Group Intimidation", "Property Damage"
]
locations = [
    "Platform A - Gate 1", "Main Entrance CCTV", "Parking Lot B",
    "Corridor 3 - Camera 2", "Stairwell North", "CCTV Camera 4 - Exit",
    "Bus Stop Outside", "Elevator Block C"
]
descriptions = [
    "Subject observed exhibiting aggressive posture towards victim for over 3 minutes.",
    "AI model flagged rapid erratic motion pattern. Confidence 82%.",
    "Sustained close-proximity behavior with blocking exit pattern detected.",
    "Individual followed subject across 3 camera zones over 8 minutes.",
    "Group of 4 individuals surrounded single person at ATM area.",
    "Loud verbal altercation escalated to physical contact at timestamp 04:32.",
    "AI detected repeated approach-retreat-approach pattern typical of intimidation.",
    "Subject cornered against wall by 2 individuals. High motion variance score."
]

incidents = []
now = datetime.now()
for i in range(20):
    dt = now - timedelta(hours=random.randint(1, 72*5), minutes=random.randint(0,59))
    src = random.choice(['ai', 'ai', 'manual'])
    sev = random.choice(['high', 'high', 'medium', 'medium', 'medium', 'low'])
    status = random.choice(['Open', 'Open', 'Investigating', 'Resolved'])
    inc = {
        "id": f"INC-{dt.strftime('%Y%m%d%H%M%S')}{i:02d}",
        "timestamp": dt.isoformat(),
        "type": random.choice(types),
        "location": random.choice(locations),
        "description": random.choice(descriptions),
        "severity": sev,
        "status": status,
        "source": src,
        "confidence": round(random.uniform(0.55, 0.97), 3) if src == 'ai' else None,
        "video_file": f"footage_{dt.strftime('%Y%m%d_%H%M%S')}.mp4" if src == 'ai' else None,
        "evidence_frames": [f"00:{random.randint(10,59):02d}" for _ in range(random.randint(1,4))] if src == 'ai' else []
    }
    incidents.append(inc)

incidents.sort(key=lambda x: x['timestamp'])
with open('incidents/incidents.json', 'w') as f:
    json.dump(incidents, f, indent=2)

print(f"✅ Generated {len(incidents)} demo incidents → incidents/incidents.json")
