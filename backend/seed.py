import requests

BASE = "http://localhost:5000/api"

secretary_user = {
    "email": "secretary@niwaas.in", "password": "test1234", "role": "secretary",
    "name": "Priya Menon", "phone": "9876543210",
}

security_user = {
    "email": "security@niwaas.in", "password": "test1234", "role": "security",
    "name": "Laddu Kumar", "phone": "9847891223",
}

# five residents, two onboarded, three pending — each with real flat details
residents = [
    {"email": "resident1@niwaas.in", "password": "test1234", "role": "resident",
     "name": "Ravi Kumar", "phone": "9848011223",
     "tower": "A", "floor": 4, "unit_number": "402", "flat_number": "A-402",
     "onboarded": True},
    {"email": "resident2@niwaas.in", "password": "test1234", "role": "resident",
     "name": "Arjun Nair", "phone": "9848011225",
     "tower": "C", "floor": 1, "unit_number": "105", "flat_number": "C-105",
     "onboarded": True},
    {"email": "resident3@niwaas.in", "password": "test1234", "role": "resident",
     "name": "Sana Iqbal", "phone": "9848011226",
     "tower": "A", "floor": 1, "unit_number": "108", "flat_number": "A-108",
     "onboarded": False},
    {"email": "resident4@niwaas.in", "password": "test1234", "role": "resident",
     "name": "Meena Sharma", "phone": "9848011227",
     "tower": "B", "floor": 3, "unit_number": "301", "flat_number": "B-301",
     "onboarded": False},
    {"email": "resident5@niwaas.in", "password": "test1234", "role": "resident",
     "name": "Deepak Rao", "phone": "9848011228",
     "tower": "D", "floor": 2, "unit_number": "201", "flat_number": "D-201",
     "onboarded": False},
]


def register(payload):
    r = requests.post(f"{BASE}/auth/register", json=payload)
    if r.status_code == 201:
        print(f"✓ Created {payload['email']}")
    elif r.status_code == 409:
        print(f"ℹ Already exists {payload['email']} — skipping")
    else:
        print(f"✗ Failed {payload['email']} — {r.json()}")
    return r


# 1. Secretary — created first since resident registration needs no auth,
#    but we keep the order consistent with how the real flow would run
register(secretary_user)

# 2. Residents — each registration also creates the flat inline via
#    tower/floor/unit_number/flat_number in the payload
for u in residents:
    onboarded   = u.pop("onboarded")
    reg_payload = {k: v for k, v in u.items()}

    reg_res = register(reg_payload)

    if not onboarded:
        continue

    if reg_res.status_code != 201:
        print(f"  ↳ Skipping onboarding for {u['email']} — registration did not succeed")
        continue

    invite_code = reg_res.json().get("invite_code")

    # log in as this resident to call /onboard (requires an authenticated session)
    session = requests.Session()
    login_res = session.post(f"{BASE}/auth/login", json={
        "email": u["email"], "password": u["password"],
    })
    if login_res.status_code != 200:
        print(f"  ↳ ✗ Could not log in {u['email']} to onboard — {login_res.json()}")
        continue

    onboard_res = session.post(f"{BASE}/auth/onboard", json={
        "invite_code": invite_code,
        "new_password": u["password"],  # keeping the same password; resident can change it later
    })
    if onboard_res.status_code == 200:
        print(f"  ↳ ✓ Onboarded {u['email']}")
    else:
        print(f"  ↳ ✗ Onboarding failed for {u['email']} — {onboard_res.json()}")

# 3. Security
register(security_user)