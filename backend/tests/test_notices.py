from datetime import date, timedelta


def future_date(days=7):
    return (date.today() + timedelta(days=days)).isoformat()


def past_date(days=7):
    return (date.today() - timedelta(days=days)).isoformat()


def create_notice(client, **overrides):
    payload = {
        'title': 'Water supply disruption',
        'description': 'Water will be cut off from 10 AM to 2 PM for maintenance.',
        'tag': 'Maintenance',
        'expiry_date': future_date(),
    }
    payload.update(overrides)
    return client.post('/api/notices', json=payload)


def test_secretary_can_create_notice(secretary_client):
    r = create_notice(secretary_client)
    assert r.status_code == 201
    body = r.get_json()['notice']
    assert body['title'] == 'Water supply disruption'
    assert body['is_active'] is True


def test_resident_cannot_create_notice(resident_client):
    r = create_notice(resident_client)
    assert r.status_code == 403


def test_list_notices(resident_client, secretary_client):
    create_notice(secretary_client)
    r = resident_client.get('/api/notices')
    assert r.status_code == 200
    assert r.get_json()['total'] == 1


def test_expiry_in_past_rejected(secretary_client):
    r = create_notice(secretary_client, expiry_date=past_date())
    assert r.status_code == 400


def test_secretary_can_delete_notice(secretary_client):
    notice = create_notice(secretary_client).get_json()['notice']
    r = secretary_client.delete(f"/api/notices/{notice['id']}")
    assert r.status_code == 200

    listing = secretary_client.get('/api/notices').get_json()
    assert listing['total'] == 0


