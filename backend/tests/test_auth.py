from conftest import register, login


def test_register_creates_resident(client):
    r = register(client, 'newres@test.com', 'Passw0rd1', 'resident', 'New Resident')
    assert r.status_code == 201
    body = r.get_json()
    assert body['user']['email'] == 'newres@test.com'
    assert body['user']['role'] == 'resident'
    assert 'invite_code' in body


def test_login_success(client):
    register(client, 'login1@test.com', 'Passw0rd1', 'resident', 'Login One')
    r = login(client, 'login1@test.com', 'Passw0rd1')
    assert r.status_code == 200
    assert r.get_json()['user']['email'] == 'login1@test.com'


def test_login_wrong_password(client):
    register(client, 'login2@test.com', 'Passw0rd1', 'resident', 'Login Two')
    r = login(client, 'login2@test.com', 'WrongPass1')
    assert r.status_code == 401


def test_register_duplicate_email(client):
    register(client, 'dupe@test.com', 'Passw0rd1', 'resident', 'First')
    r = register(client, 'dupe@test.com', 'Passw0rd1', 'resident', 'Second')
    assert r.status_code == 409


def test_me_requires_login(client):
    # flask-login's default unauthorized handler redirects (no custom JSON
    # handler is registered), so an unauthenticated request never reaches
    # the view — it gets bounced to the login route instead of 401/403.
    r = client.get('/api/auth/me')
    assert r.status_code == 302
