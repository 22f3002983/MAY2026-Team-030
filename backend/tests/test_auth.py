from conftest import register, login


def register_resident(client, email, name, **overrides):
    payload = {'flat_number': 'A-101', 'tower': 'A', 'floor': 1, 'unit_number': '101'}
    payload.update(overrides)
    return register(client, email, 'Passw0rd1', 'resident', name, **payload)


def test_register_creates_resident(client):
    r = register_resident(client, 'newres@test.com', 'New Resident')
    assert r.status_code == 201
    body = r.get_json()
    assert body['user']['email'] == 'newres@test.com'
    assert body['user']['role'] == 'resident'
    assert 'invite_code' in body


def test_login_success(client):
    reg = register_resident(client, 'login1@test.com', 'Login One')
    invite_code = reg.get_json()['invite_code']
    r = login(client, 'login1@test.com', 'Passw0rd1', invite_code=invite_code)
    assert r.status_code == 200
    assert r.get_json()['user']['email'] == 'login1@test.com'


def test_login_wrong_password(client):
    register_resident(client, 'login2@test.com', 'Login Two')
    r = login(client, 'login2@test.com', 'WrongPass1')
    assert r.status_code == 401


def test_register_duplicate_email(client):
    register_resident(client, 'dupe@test.com', 'First', flat_number='A-101', unit_number='101')
    r = register_resident(client, 'dupe@test.com', 'Second', flat_number='A-102', unit_number='102')
    assert r.status_code == 409


def test_me_requires_login(client):
    # flask-login's default unauthorized handler redirects (no custom JSON
    # handler is registered), so an unauthenticated request never reaches
    # the view — it gets bounced to the login route instead of 401/403.
    r = client.get('/api/auth/me')
    assert r.status_code == 302