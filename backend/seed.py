import requests

BASE = "http://localhost:5000/api/auth/register"

users = [
    {"email": "secretary@niwaas.in", "password": "test1234", "role": "secretary", "name": "Priya Menon", "phone": "9876543210"},
    {"email": "resident@niwaas.in",  "password": "test1234", "role": "resident",  "name": "Ravi Kumar",  "phone": "9848011223"},
]

for u in users:
    r = requests.post(BASE, json=u)
    if r.status_code == 201:
        print(f"✓ Created {u['email']}")
    elif r.status_code == 409:
        print(f"ℹ Already exists {u['email']} — skipping")
    else:
        print(f"✗ Failed {u['email']} — {r.json()}")