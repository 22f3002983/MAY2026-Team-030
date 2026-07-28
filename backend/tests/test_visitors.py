def pre_register(client, name='Rahul Verma', **overrides):
    payload = {'name': name, 'phone': '9876543210'}
    payload.update(overrides)
    return client.post('/api/visitors', json=payload)


def test_resident_can_pre_register_visitor(resident_client):
    r = pre_register(resident_client)
    assert r.status_code == 201
    body = r.get_json()
    assert body['pass_code'].startswith('GATE-')
    assert body['visitor']['status'] == 'pre_registered'


def test_pass_codes_are_unique(resident_client):
    p1 = pre_register(resident_client, name='Visitor One').get_json()['pass_code']
    p2 = pre_register(resident_client, name='Visitor Two').get_json()['pass_code']
    assert p1 != p2


def test_security_can_verify_valid_pass_code(resident_client, security_client):
    pass_code = pre_register(resident_client).get_json()['pass_code']

    r = security_client.patch('/api/visitors/verify', json={'pass_code': pass_code})
    assert r.status_code == 200
    assert r.get_json()['visitor']['pass_code'] == pass_code


def test_security_verify_invalid_pass_code(security_client):
    r = security_client.patch('/api/visitors/verify', json={'pass_code': 'GATE-0000'})
    assert r.status_code == 404


def test_security_can_check_in_visitor(resident_client, security_client):
    visitor = pre_register(resident_client).get_json()['visitor']

    r = security_client.patch(f"/api/visitors/{visitor['id']}/checkin")
    assert r.status_code == 200
    updated = r.get_json()['visitor']
    assert updated['status'] == 'checked_in'
    assert updated['id_verified'] is True
    assert updated['check_in_time'] is not None
