from datetime import date, timedelta


def add_vendor(client, **overrides):
    payload = {'name': 'Kishore Plumbing', 'phone': '9900011122', 'category': 'plumber'}
    payload.update(overrides)
    return client.post('/api/vendors', json=payload)


def book_service(client, vendor_id, **overrides):
    payload = {
        'category': 'plumber',
        'description': 'Leaking kitchen tap',
        'vendor_id': vendor_id,
        'scheduled_date': (date.today() + timedelta(days=3)).isoformat(),
        'scheduled_time': '10:00',
    }
    payload.update(overrides)
    return client.post('/api/service-requests', json=payload)


def test_resident_can_book_service(resident_client, secretary_client):
    vendor = add_vendor(secretary_client).get_json()['vendor']
    r = book_service(resident_client, vendor['id'])
    assert r.status_code == 201
    body = r.get_json()['request']
    assert body['status'] == 'scheduled'
    assert body['duration_minutes'] == 60


def test_invalid_category_rejected(resident_client, secretary_client):
    vendor = add_vendor(secretary_client).get_json()['vendor']
    r = book_service(resident_client, vendor['id'], category='not-a-category')
    assert r.status_code == 400


def test_missing_schedule_rejected(resident_client, secretary_client):
    vendor = add_vendor(secretary_client).get_json()['vendor']
    r = resident_client.post('/api/service-requests', json={
        'category': 'plumber', 'description': 'Leaking tap', 'vendor_id': vendor['id'],
    })
    assert r.status_code == 400


def test_reschedule_only_when_scheduled(resident_client, secretary_client):
    vendor = add_vendor(secretary_client).get_json()['vendor']
    sr = book_service(resident_client, vendor['id']).get_json()['request']

    r = resident_client.patch(f"/api/service-requests/{sr['id']}", json={'scheduled_time': '14:00'})
    assert r.status_code == 200
    assert r.get_json()['request']['scheduled_time'].startswith('14:00')

    resident_client.patch(f"/api/service-requests/{sr['id']}/cancel")
    r2 = resident_client.patch(f"/api/service-requests/{sr['id']}", json={'scheduled_time': '15:00'})
    assert r2.status_code == 400


def test_cancel_request(resident_client, secretary_client):
    vendor = add_vendor(secretary_client).get_json()['vendor']
    sr = book_service(resident_client, vendor['id']).get_json()['request']

    r = resident_client.patch(f"/api/service-requests/{sr['id']}/cancel")
    assert r.status_code == 200
    assert r.get_json()['request']['status'] == 'cancelled'


def test_complete_request_records_payment(resident_client, secretary_client):
    vendor = add_vendor(secretary_client).get_json()['vendor']
    sr = book_service(resident_client, vendor['id']).get_json()['request']

    r = resident_client.patch(f"/api/service-requests/{sr['id']}/complete", json={'amount': 500})
    assert r.status_code == 200
    body = r.get_json()['request']
    assert body['status'] == 'completed'
    assert body['payment_status'] == 'paid'
    assert body['payment_amount'] == 500.0


def test_rate_only_after_complete(resident_client, secretary_client):
    vendor = add_vendor(secretary_client).get_json()['vendor']
    sr = book_service(resident_client, vendor['id']).get_json()['request']

    pre = resident_client.patch(f"/api/service-requests/{sr['id']}/rate", json={'rating': 5})
    assert pre.status_code == 400

    resident_client.patch(f"/api/service-requests/{sr['id']}/complete", json={'amount': 500})
    r = resident_client.patch(f"/api/service-requests/{sr['id']}/rate", json={'rating': 5})
    assert r.status_code == 200
    assert r.get_json()['request']['rating'] == 5


def test_list_requests_filtered_by_status(resident_client, secretary_client):
    vendor = add_vendor(secretary_client).get_json()['vendor']
    sr = book_service(resident_client, vendor['id']).get_json()['request']
    resident_client.patch(f"/api/service-requests/{sr['id']}/cancel")

    r = resident_client.get('/api/service-requests?status=cancelled')
    assert r.status_code == 200
    assert r.get_json()['total'] == 1

    r2 = resident_client.get('/api/service-requests?status=scheduled')
    assert r2.get_json()['total'] == 0