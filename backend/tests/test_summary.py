from datetime import date, timedelta


def create_notice(client, **overrides):
    payload = {
        'title': 'Water supply disruption',
        'description': 'Water will be cut off from 10 AM to 2 PM for maintenance.',
        'tag': 'Maintenance',
        'expiry_date': (date.today() + timedelta(days=7)).isoformat(),
    }
    payload.update(overrides)
    return client.post('/api/notices', json=payload)


def raise_complaint(client, **overrides):
    payload = {
        'title': 'Leaking pipe',
        'description': 'Water leaking near the lift lobby',
        'category': 'plumbing',
        'type': 'common_area',
    }
    payload.update(overrides)
    return client.post('/api/complaints', json=payload)


def add_vendor(client, **overrides):
    payload = {'name': 'Kishore Plumbing', 'phone': '9900011122', 'category': 'plumber'}
    payload.update(overrides)
    return client.post('/api/vendors', json=payload)


def test_resident_summary_defaults_on_fresh_account(resident_client):
    r = resident_client.get('/api/summary/resident')
    assert r.status_code == 200
    body = r.get_json()
    assert body['open_complaints'] == 0
    assert body['pending_due'] == 0
    assert body['upcoming_booking'] is None


def test_resident_summary_reflects_open_complaint(resident_client):
    raise_complaint(resident_client)
    r = resident_client.get('/api/summary/resident')
    body = r.get_json()
    assert body['open_complaints'] == 1
    assert len(body['recent_complaints']) == 1


def test_resident_summary_shows_latest_notice(resident_client, secretary_client):
    create_notice(secretary_client)
    r = resident_client.get('/api/summary/resident')
    assert r.get_json()['latest_notice']['title'] == 'Water supply disruption'


def test_secretary_summary_reflects_data(resident_client, secretary_client):
    raise_complaint(resident_client)
    add_vendor(secretary_client)
    create_notice(secretary_client)

    r = secretary_client.get('/api/summary/secretary')
    assert r.status_code == 200
    body = r.get_json()
    assert body['open_complaints'] == 1
    assert body['active_vendors'] == 1
    assert body['unread_notices'] == 1
    assert body['unassigned'] == 1


def test_security_summary_defaults(security_client):
    r = security_client.get('/api/summary/security')
    assert r.status_code == 200
    body = r.get_json()
    assert body['visitors_inside'] == 0
    assert body['awaiting_approval'] == 0


def test_summary_routes_are_role_locked(resident_client, secretary_client, security_client):
    assert secretary_client.get('/api/summary/resident').status_code == 403
    assert resident_client.get('/api/summary/secretary').status_code == 403
    assert resident_client.get('/api/summary/security').status_code == 403