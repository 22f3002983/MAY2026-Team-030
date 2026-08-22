"""
Seed script for the Niwaas RWA backend.

Populates the running Flask app (via its HTTP API — no direct DB access)
with a realistic set of demo data:

  • 1 secretary + 1 security guard
  • 6 residents across 4 towers — 3 onboarded, 3 still pending first login
  • 2 vendors (plumbing, electrical)
  • 6 amenities (pool, clubhouse, gym, tennis court, garden, community hall)
    + a handful of bookings (auto-approved, pending, and secretary-approved)
  • 6 notices (General / Maintenance / Security / Event / Urgent)
  • 6 complaint reports across 5 community issues (including one issue with
    two reporters, one assigned to a vendor, one resolved with feedback)

Usage:
    1. Start the backend:  python run.py   (default: http://localhost:5000)
    2. In another shell:   python seed.py

Safe to re-run — anything that already exists (matched by email, for
example) is skipped rather than duplicated; the script just logs it and
moves on.
"""

import sys
import requests

BASE = "http://localhost:5000/api"


# ─────────────────────────────────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────────────────────────────────

secretary_user = {
    "email": "secretary@niwaas.in", "password": "test1234", "role": "secretary",
    "name": "Priya Menon", "phone": "9876543210",
}

security_user = {
    "email": "security@niwaas.in", "password": "test1234", "role": "security",
    "name": "Laddu Kumar", "phone": "9847891223",
}

# six residents across four towers — three onboarded (have logged in with
# their invite code at least once), three still pending first login
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
    {"email": "resident6@niwaas.in", "password": "test1234", "role": "resident",
     "name": "Kavya Reddy", "phone": "9848011229",
     "tower": "B", "floor": 2, "unit_number": "205", "flat_number": "B-205",
     "onboarded": True},
]

vendors = [
    {"name": "Suresh Plumbing Works", "phone": "9900011122", "category": "plumbing",
     "description": "General plumbing repairs and installations", "working_hours": "9 AM - 7 PM"},
    {"name": "Bright Spark Electricals", "phone": "9900011133", "category": "electrical",
     "description": "Electrical wiring, fixtures and repairs", "working_hours": "10 AM - 6 PM"},
]

amenities = [
    {"name": "Swimming Pool", "type": "public", "booking_type": "automatic",
     "icon": "🏊", "location": "Clubhouse Level 1", "capacity": 30,
     "description": "Outdoor swimming pool, open to all residents.",
     "features": ["Lifeguard on duty", "Poolside seating"],
     "pricing": {"type": "hourly", "rate": 100, "min_units": 1, "unit_label": "hour"}},
    {"name": "Clubhouse Banquet Hall", "type": "exclusive", "booking_type": "approval_required",
     "icon": "🎉", "location": "Clubhouse Level 2", "capacity": 150,
     "description": "Large hall for weddings, birthdays and society events.",
     "is_air_conditioned": True, "is_decoratable": True,
     "features": ["Stage", "Sound system", "Catering pantry"],
     "pricing": {"type": "daily", "rate": 5000, "min_units": 1, "unit_label": "day"}},
    {"name": "Gymnasium", "type": "public", "booking_type": "automatic",
     "icon": "🏋️", "location": "Tower A Ground Floor", "capacity": 20,
     "is_air_conditioned": True,
     "description": "Fully equipped gym with cardio and free weights.",
     "features": ["Treadmills", "Free weights", "Yoga mats"]},
    {"name": "Tennis Court", "type": "public", "booking_type": "automatic",
     "icon": "🎾", "location": "Behind Tower D", "capacity": 4,
     "description": "Synthetic hard-court, floodlit for evening play.",
     "features": ["Floodlights", "Equipment rental on request"],
     "pricing": {"type": "hourly", "rate": 50, "min_units": 1, "unit_label": "hour"}},
    {"name": "Garden & Jogging Track", "type": "unbookable",
     "icon": "🌳", "location": "Central Courtyard",
     "description": "Landscaped garden with a 600m jogging track, open 24x7."},
    {"name": "Community Hall", "type": "exclusive", "booking_type": "approval_required",
     "icon": "🏛️", "location": "Tower C Ground Floor", "capacity": 60,
     "is_air_conditioned": True, "is_decoratable": True,
     "description": "Mid-sized hall for kitty parties, meetings and small functions.",
     "features": ["Projector", "Whiteboard", "Folding chairs"],
     "pricing": {"type": "daily", "rate": 3000, "min_units": 1, "unit_label": "day"}},
]

notices = [
    {"title": "Annual General Meeting — 2026", "tag": "Event", "priority": "normal",
     "expiry_date": "2026-09-30",
     "description": "The AGM will be held in the Clubhouse Banquet Hall on 30th September at 6 PM. "
                     "All residents are requested to attend and carry their flat ownership documents."},
    {"title": "Scheduled Water Supply Maintenance", "tag": "Maintenance", "priority": "normal",
     "expiry_date": "2026-08-25",
     "description": "Water supply will be interrupted on 22nd August from 10 AM to 2 PM for overhead "
                     "tank cleaning. Please store water in advance."},
    {"title": "New Security Shift Timings", "tag": "Security", "priority": "normal",
     "expiry_date": "2026-09-15",
     "description": "Security guard shifts are changing to 8-hour rotations effective 1st September. "
                     "Gate staff will carry updated ID badges."},
    {"title": "Diwali Celebration & Potluck", "tag": "Event", "priority": "normal",
     "expiry_date": "2026-11-10",
     "description": "Join us for the society Diwali get-together in the garden on 8th November, 7 PM "
                     "onwards. Please bring a dish to share for the potluck."},
    {"title": "Visitor Parking Rules — Reminder", "tag": "General", "priority": "normal",
     "expiry_date": "2026-10-01",
     "description": "Visitor vehicles must be parked only in the designated visitor bays near the main "
                     "gate. Vehicles blocking driveways will be towed at the owner's cost."},
    {"title": "Mandatory Fire Safety Drill", "tag": "Urgent", "priority": "urgent",
     "expiry_date": "2026-08-30",
     "description": "A fire evacuation drill will be conducted across all towers on 24th August at "
                     "11 AM. All residents must participate — this is mandatory as per fire NOC conditions."},
]

# each entry raised by resident_email; issues sharing the same (title, category)
# get merged into one CommunityIssue by the backend, so #1 and #4 below
# collapse into a single two-reporter issue
complaints = [
    {"resident_email": "resident1@niwaas.in", "title": "Leaking pipe under kitchen sink",
     "description": "There has been a steady water leak under the kitchen sink for two days, "
                     "the cabinet is getting damaged.",
     "category": "plumbing", "type": "personal", "location": "A-402", "priority": "high"},
    {"resident_email": "resident2@niwaas.in", "title": "Streetlight not working near Tower C",
     "description": "The streetlight near the Tower C parking has been off for over a week, "
                     "it's quite dark and unsafe at night.",
     "category": "electrical", "type": "common_area", "location": "Tower C parking", "priority": "medium"},
    {"resident_email": "resident6@niwaas.in", "title": "Garbage not collected from B block bins",
     "description": "Garbage bins outside Tower B ground floor haven't been emptied in three days.",
     "category": "cleaning", "type": "common_area", "location": "Tower B ground floor", "priority": "medium"},
    {"resident_email": "resident1@niwaas.in", "title": "Streetlight not working near Tower C",
     "description": "Confirming this too — walked past it yesterday evening and it's still out.",
     "category": "electrical", "type": "common_area", "location": "Tower C parking", "priority": "medium"},
    {"resident_email": "resident2@niwaas.in", "title": "Lift making loud grinding noise",
     "description": "The Tower C lift makes a loud grinding noise between the 1st and 2nd floors, "
                     "feels unsafe.",
     "category": "other", "type": "common_area", "location": "Tower C lift", "priority": "high"},
    {"resident_email": "resident6@niwaas.in", "title": "Termites in wooden wardrobe",
     "description": "Found termite trails inside the bedroom wardrobe, needs pest control treatment.",
     "category": "pest_control", "type": "personal", "location": "B-205", "priority": "low"},
]


# ─────────────────────────────────────────────────────────────────────────
# HTTP helpers
# ─────────────────────────────────────────────────────────────────────────

def register(payload):
    r = requests.post(f"{BASE}/auth/register", json=payload)
    if r.status_code == 201:
        print(f"✓ Created {payload['email']}")
    elif r.status_code == 409:
        print(f"ℹ Already exists {payload['email']} — skipping")
    else:
        print(f"✗ Failed {payload['email']} — {safe_json(r)}")
    return r


def login(email, password, invite_code=None):
    """Returns an authenticated requests.Session(), or None on failure."""
    session = requests.Session()
    body = {"email": email, "password": password}
    if invite_code:
        body["invite_code"] = invite_code
    r = session.post(f"{BASE}/auth/login", json=body)
    if r.status_code != 200:
        print(f"  ↳ ✗ Login failed for {email} — {safe_json(r)}")
        return None
    return session


def safe_json(response):
    try:
        return response.json()
    except ValueError:
        return response.text[:200]


def server_is_up():
    try:
        r = requests.get(f"{BASE}/auth/ping", timeout=3)
        return r.status_code == 200
    except requests.exceptions.ConnectionError:
        return False


# ─────────────────────────────────────────────────────────────────────────
# 1. Secretary + Security
# ─────────────────────────────────────────────────────────────────────────

def seed_secretary_and_security():
    print("\n== Secretary & Security ==")
    register(secretary_user)
    register(security_user)


# ─────────────────────────────────────────────────────────────────────────
# 2. Residents (register + onboard where flagged)
# ─────────────────────────────────────────────────────────────────────────

def seed_residents():
    print("\n== Residents ==")
    resident_sessions = {}  # email -> authenticated session (onboarded only)

    for u in residents:
        onboarded = u["onboarded"]
        reg_payload = {k: v for k, v in u.items() if k != "onboarded"}

        reg_res = register(reg_payload)

        if reg_res.status_code == 201:
            invite_code = reg_res.json().get("invite_code")
        elif reg_res.status_code == 409:
            invite_code = None  # already registered in an earlier run
        else:
            print(f"  ↳ Skipping {u['email']} — registration did not succeed")
            continue

        if not onboarded:
            continue

        # first login consumes the invite code and flips is_onboarded=True;
        # on a re-run (already onboarded) the invite code is no longer
        # required, so a plain login still succeeds
        session = login(u["email"], u["password"], invite_code=invite_code)
        if session:
            print(f"  ↳ ✓ Onboarded & logged in {u['email']}")
            resident_sessions[u["email"]] = session
        else:
            print(f"  ↳ ✗ Could not onboard {u['email']}")

    return resident_sessions


# ─────────────────────────────────────────────────────────────────────────
# 3. Vendors (secretary)
# ─────────────────────────────────────────────────────────────────────────

def seed_vendors(secretary_session):
    print("\n== Vendors ==")
    vendor_ids = {}  # category -> vendor id
    for v in vendors:
        r = secretary_session.post(f"{BASE}/vendors", json=v)
        if r.status_code == 201:
            vendor = r.json()["vendor"]
            vendor_ids[v["category"]] = vendor["id"]
            print(f"✓ Added vendor {v['name']}")
        else:
            print(f"✗ Failed to add vendor {v['name']} — {safe_json(r)}")
    return vendor_ids


# ─────────────────────────────────────────────────────────────────────────
# 4. Amenities + a few bookings (secretary creates, residents book)
# ─────────────────────────────────────────────────────────────────────────

def seed_amenities(secretary_session, resident_sessions):
    print("\n== Amenities ==")
    amenity_ids = {}  # name -> id
    for a in amenities:
        r = secretary_session.post(f"{BASE}/amenities", json=a)
        if r.status_code == 201:
            amenity = r.json()["amenity"]
            amenity_ids[a["name"]] = amenity["id"]
            print(f"✓ Added amenity {a['name']}")
        else:
            print(f"✗ Failed to add amenity {a['name']} — {safe_json(r)}")

    print("\n== Amenity bookings ==")
    bookings_to_make = [
        # (resident_email, amenity_name, payload)
        ("resident1@niwaas.in", "Gymnasium", {
            "date": "2026-08-20", "event_type": "Personal workout", "guests": 1,
        }),
        ("resident2@niwaas.in", "Tennis Court", {
            "date": "2026-08-21", "event_type": "Friendly match", "guests": 2,
            "start_time": "17:00", "end_time": "18:00",
        }),
        ("resident6@niwaas.in", "Clubhouse Banquet Hall", {
            "date": "2026-09-05", "end_date": "2026-09-05",
            "event_type": "Birthday party", "guests": 80,
        }),
    ]

    pending_booking_ids = []
    for email, amenity_name, payload in bookings_to_make:
        session = resident_sessions.get(email)
        amenity_id = amenity_ids.get(amenity_name)
        if not session or not amenity_id:
            continue
        r = session.post(f"{BASE}/amenities/{amenity_id}/book", json=payload)
        if r.status_code == 201:
            booking = r.json()["booking"]
            status_note = f"({booking['status']})"
            print(f"✓ {email} booked {amenity_name} {status_note}")
            if booking["status"] == "pending":
                pending_booking_ids.append(booking["id"])
        else:
            print(f"✗ Booking failed for {email} on {amenity_name} — {safe_json(r)}")

    # secretary approves any pending (approval_required) bookings, e.g. the
    # Clubhouse Banquet Hall booking above
    for booking_id in pending_booking_ids:
        r = secretary_session.patch(f"{BASE}/amenities/bookings/{booking_id}/approve")
        if r.status_code == 200:
            print(f"✓ Secretary approved booking {booking_id}")
        else:
            print(f"✗ Could not approve booking {booking_id} — {safe_json(r)}")

    return amenity_ids


# ─────────────────────────────────────────────────────────────────────────
# 5. Notices (secretary)
# ─────────────────────────────────────────────────────────────────────────

def seed_notices(secretary_session):
    print("\n== Notices ==")
    for n in notices:
        r = secretary_session.post(f"{BASE}/notices", json=n)
        if r.status_code == 201:
            print(f"✓ Posted notice: {n['title']}")
        else:
            print(f"✗ Failed to post notice {n['title']} — {safe_json(r)}")


# ─────────────────────────────────────────────────────────────────────────
# 6. Complaints (residents raise, secretary assigns/resolves, feedback)
# ─────────────────────────────────────────────────────────────────────────

def seed_complaints(secretary_session, resident_sessions, vendor_ids):
    print("\n== Complaints ==")
    created = []  # (complaint_id, title, resident_email)

    for c in complaints:
        session = resident_sessions.get(c["resident_email"])
        if not session:
            print(f"✗ Skipping complaint '{c['title']}' — {c['resident_email']} not onboarded")
            continue
        payload = {k: v for k, v in c.items() if k != "resident_email"}
        r = session.post(f"{BASE}/complaints", json=payload)
        if r.status_code == 201:
            complaint = r.json()["complaint"]
            created.append((complaint["id"], c["title"], c["resident_email"]))
            print(f"✓ {c['resident_email']} raised: {c['title']}")
        else:
            print(f"✗ Failed to raise '{c['title']}' — {safe_json(r)}")

    if not created:
        return

    # find the two complaints of interest by title
    by_title = {}
    for cid, title, email in created:
        by_title.setdefault(title, []).append(cid)

    # 1) assign the plumbing complaint to the plumber and mark it resolved,
    #    then have the reporting resident leave feedback
    plumbing_ids = by_title.get("Leaking pipe under kitchen sink", [])
    plumber_id = vendor_ids.get("plumber")
    if plumbing_ids and plumber_id:
        complaint_id = plumbing_ids[0]
        r = secretary_session.patch(f"{BASE}/complaints/{complaint_id}/assign",
                                     json={"vendor_id": plumber_id})
        print("✓ Assigned plumber to leaking pipe complaint" if r.status_code == 200
              else f"✗ Assign failed — {safe_json(r)}")

        r = secretary_session.patch(f"{BASE}/complaints/{complaint_id}/status",
                                     json={"status": "resolved"})
        print("✓ Marked leaking pipe complaint resolved" if r.status_code == 200
              else f"✗ Status update failed — {safe_json(r)}")

        resident_session = resident_sessions.get("resident1@niwaas.in")
        if resident_session:
            r = resident_session.patch(f"{BASE}/complaints/{complaint_id}/feedback",
                                        json={"feedback_rating": 5,
                                              "feedback_comment": "Fixed quickly, thank you!"})
            print("✓ Feedback submitted for leaking pipe complaint" if r.status_code == 200
                  else f"✗ Feedback failed — {safe_json(r)}")

    # 2) assign the streetlight issue (2 reporters) to the electrician and
    #    move it to in_progress
    streetlight_ids = by_title.get("Streetlight not working near Tower C", [])
    electrician_id = vendor_ids.get("electrical")
    if streetlight_ids and electrician_id:
        complaint_id = streetlight_ids[0]
        r = secretary_session.patch(f"{BASE}/complaints/{complaint_id}/assign",
                                     json={"vendor_id": electrician_id})
        print("✓ Assigned electrician to streetlight issue (2 reporters)" if r.status_code == 200
              else f"✗ Assign failed — {safe_json(r)}")


# ─────────────────────────────────────────────────────────────────────────
# main
# ─────────────────────────────────────────────────────────────────────────

def main():
    if not server_is_up():
        print(f"✗ Could not reach the backend at {BASE}.")
        print("  Start it first with:  python run.py")
        sys.exit(1)

    seed_secretary_and_security()
    resident_sessions = seed_residents()

    secretary_session = login(secretary_user["email"], secretary_user["password"])
    if not secretary_session:
        print("✗ Could not log in as secretary — aborting remaining steps.")
        sys.exit(1)

    vendor_ids = seed_vendors(secretary_session)
    seed_amenities(secretary_session, resident_sessions)
    seed_notices(secretary_session)
    seed_complaints(secretary_session, resident_sessions, vendor_ids)

    print("\n✓ Seeding complete.")
    print("  Login as secretary@niwaas.in / test1234, security@niwaas.in / test1234,")
    print("  or any onboarded resident (resident1, resident2, resident6 @niwaas.in) / test1234.")


if __name__ == "__main__":
    main()