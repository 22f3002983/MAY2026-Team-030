from datetime import date, timedelta


def booking_date():
    return (date.today() + timedelta(days=10)).isoformat()


def add_amenity(client, **overrides):
    payload = {
        'name': 'Community Hall',
        'type': 'exclusive',
        'booking_type': 'approval_required',
        'description': 'A large hall for events.',
    }
    payload.update(overrides)
    return client.post('/api/amenities', json=payload)


def book(client, amenity_id, **overrides):
    payload = {'date': booking_date(), 'event_type': 'Birthday party', 'guests': 20}
    payload.update(overrides)
    return client.post(f'/api/amenities/{amenity_id}/book', json=payload)


def test_secretary_can_add_amenity(secretary_client):
    r = add_amenity(secretary_client)
    assert r.status_code == 201
    body = r.get_json()['amenity']
    assert body['name'] == 'Community Hall'
    assert body['status'] == 'available'


def test_resident_can_book_amenity_pending_approval(resident_client, secretary_client):
    amenity = add_amenity(secretary_client).get_json()['amenity']
    r = book(resident_client, amenity['id'])
    assert r.status_code == 201
    booking = r.get_json()['booking']
    assert booking['status'] == 'pending'


def test_booking_conflicts_with_existing_pending_booking(resident_client, secretary_client):
    # a pending booking already holds the slot tentatively — a second
    # booking for the same amenity/date is rejected at creation time,
    # it never even reaches the secretary for approval.
    amenity = add_amenity(secretary_client).get_json()['amenity']

    r1 = book(resident_client, amenity['id'])
    assert r1.status_code == 201

    r2 = book(resident_client, amenity['id'])
    assert r2.status_code == 409


def test_secretary_can_approve_booking(resident_client, secretary_client):
    amenity = add_amenity(secretary_client).get_json()['amenity']
    booking = book(resident_client, amenity['id']).get_json()['booking']

    r = secretary_client.patch(f"/api/amenities/bookings/{booking['id']}/approve")
    assert r.status_code == 200
    assert r.get_json()['booking']['status'] == 'approved'


def test_cancelled_booking_frees_the_slot(resident_client, secretary_client):
    amenity = add_amenity(secretary_client).get_json()['amenity']
    booking = book(resident_client, amenity['id']).get_json()['booking']

    cancel = resident_client.patch(f"/api/amenities/bookings/{booking['id']}/cancel")
    assert cancel.status_code == 200
    assert cancel.get_json()['booking']['status'] == 'cancelled'

    # same slot should now be bookable again
    r2 = book(resident_client, amenity['id'])
    assert r2.status_code == 201


def test_reject_booking(resident_client, secretary_client):
    amenity = add_amenity(secretary_client).get_json()['amenity']
    booking = book(resident_client, amenity['id']).get_json()['booking']

    r = secretary_client.patch(f"/api/amenities/bookings/{booking['id']}/reject", json={'reason': 'Hall unavailable'})
    assert r.status_code == 200
    assert r.get_json()['booking']['status'] == 'rejected'


def test_resident_cannot_add_amenity(resident_client):
    r = add_amenity(resident_client)
    assert r.status_code == 403