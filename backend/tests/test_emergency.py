def create_alert(client, alert_type='Public', message='Fire drill at 4 PM today.'):
    return client.post('/api/emergency', json={'type': alert_type, 'message': message})


# ── create ──────────────────────────────────────────────────

def test_create_alert(secretary_client):
    r = create_alert(secretary_client, 'Public', 'Fire drill scheduled')
    assert r.status_code == 201
    body = r.get_json()['alert']
    assert body['type'] == 'Public'
    assert body['status'] == 'active'


def test_invalid_type_rejected(secretary_client):
    r = create_alert(secretary_client, alert_type='NotAType')
    assert r.status_code == 400


def test_message_required(secretary_client):
    r = secretary_client.post('/api/emergency', json={'type': 'Public', 'message': '   '})
    assert r.status_code == 400
    assert 'message' in r.get_json()['error']


def test_no_body_rejected(secretary_client):
    r = secretary_client.post('/api/emergency', content_type='application/json', data='')
    assert r.status_code == 400


def test_invalid_severity_rejected(secretary_client):
    r = secretary_client.post('/api/emergency', json={
        'type': 'Public',
        'message': 'Test alert',
        'severity': 'catastrophic',  # not one of low/medium/high/critical
    })
    assert r.status_code == 400
    assert 'severity' in r.get_json()['error']


def test_valid_severity_accepted(secretary_client):
    r = secretary_client.post('/api/emergency', json={
        'type': 'Public',
        'message': 'Test alert',
        'severity': 'high',
    })
    assert r.status_code == 201
    assert r.get_json()['alert']['severity'] == 'high'


# ── list / visibility ──────────────────────────────────────

def test_resident_sees_only_public_alerts(resident_client, secretary_client, security_client):
    create_alert(secretary_client, 'Public', 'Public alert')
    create_alert(security_client, 'Private', 'Private alert')

    r = resident_client.get('/api/emergency')
    alerts = r.get_json()['alerts']
    assert len(alerts) == 1
    assert alerts[0]['type'] == 'Public'


def test_resident_sees_own_private_alert(resident_client, security_client):
    # resident's own private alert (e.g. SOS) must still be visible to them
    create_alert(resident_client, 'Private', 'SOS from resident')
    # a private alert from someone else should stay hidden
    create_alert(security_client, 'Private', 'Someone else\'s private alert')

    r = resident_client.get('/api/emergency')
    alerts = r.get_json()['alerts']
    assert len(alerts) == 1
    assert alerts[0]['message'] == 'SOS from resident'


def test_secretary_and_security_see_all_alerts(secretary_client, security_client):
    create_alert(secretary_client, 'Public', 'Public alert')
    create_alert(security_client, 'Private', 'Private alert')

    r = secretary_client.get('/api/emergency')
    assert r.get_json()['total'] == 2

    r2 = security_client.get('/api/emergency')
    assert r2.get_json()['total'] == 2


def test_status_filter(secretary_client):
    alert = create_alert(secretary_client, 'Public', 'To be resolved').get_json()['alert']
    create_alert(secretary_client, 'Public', 'Stays active')
    secretary_client.patch(f"/api/emergency/{alert['id']}/resolve")

    r = secretary_client.get('/api/emergency?status=resolved')
    alerts = r.get_json()['alerts']
    assert len(alerts) == 1
    assert alerts[0]['id'] == alert['id']


# ── get single alert ────────────────────────────────────────

def test_get_single_alert(secretary_client):
    alert = create_alert(secretary_client, 'Public', 'Fetch me').get_json()['alert']
    r = secretary_client.get(f"/api/emergency/{alert['id']}")
    assert r.status_code == 200
    assert r.get_json()['id'] == alert['id']


def test_get_single_alert_not_found(secretary_client):
    r = secretary_client.get('/api/emergency/does-not-exist')
    assert r.status_code == 404


# ── resolve ─────────────────────────────────────────────────

def test_resolve_alert(secretary_client):
    alert = create_alert(secretary_client).get_json()['alert']
    r = secretary_client.patch(f"/api/emergency/{alert['id']}/resolve")
    assert r.status_code == 200
    assert r.get_json()['alert']['status'] == 'resolved'
    assert r.get_json()['alert']['resolved_at'] is not None


def test_security_can_resolve_alert(secretary_client, security_client):
    alert = create_alert(secretary_client).get_json()['alert']
    r = security_client.patch(f"/api/emergency/{alert['id']}/resolve")
    assert r.status_code == 200
    assert r.get_json()['alert']['status'] == 'resolved'


def test_resident_cannot_resolve_alert(secretary_client, resident_client):
    alert = create_alert(secretary_client).get_json()['alert']
    r = resident_client.patch(f"/api/emergency/{alert['id']}/resolve")
    assert r.status_code == 403


def test_resolve_nonexistent_alert(secretary_client):
    r = secretary_client.patch('/api/emergency/does-not-exist/resolve')
    assert r.status_code == 404