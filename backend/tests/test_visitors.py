def pre_register(client, name='Rahul Verma', **overrides):
    payload = {'name': name, 'phone': '9876543210'}
    payload.update(overrides)
    return client.post('/api/visitors', json=payload)


def test_mark_expired_visitors_flips_the_stored_flag(app, resident_client):
    from datetime import datetime, timedelta
    from app.extensions import db
    from app.models.visitor import Visitor
    from app.scheduler import mark_expired_visitors

    visitor_id = pre_register(resident_client).get_json()['visitor']['id']

    with app.app_context():
        visitor = Visitor.query.get(visitor_id)
        assert visitor.is_expired is False
        # backdate expires_at so this pass is already timed out
        visitor.expires_at = datetime.utcnow() - timedelta(minutes=1)
        db.session.commit()

        mark_expired_visitors(app)

        refreshed = Visitor.query.get(visitor_id)
        assert refreshed.is_expired is True


def test_mark_expired_visitors_leaves_active_passes_alone(app, resident_client):
    from datetime import datetime, timedelta
    from app.extensions import db
    from app.models.visitor import Visitor
    from app.scheduler import mark_expired_visitors

    visitor_id = pre_register(resident_client).get_json()['visitor']['id']

    with app.app_context():
        visitor = Visitor.query.get(visitor_id)
        visitor.expires_at = datetime.utcnow() + timedelta(hours=1)
        db.session.commit()

        mark_expired_visitors(app)

        refreshed = Visitor.query.get(visitor_id)
        assert refreshed.is_expired is False


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


def test_verify_checked_in_visitor_shows_already_in_even_if_pass_revoked(resident_client, security_client):
    """The exact bug this guards against: a visitor is checked in, then the
    resident revokes their pass. Re-scanning at the gate must still report
    'checked in' (status) rather than bouncing on the revoked pass — the
    person is still on the property and security needs the checkout
    shortcut, not a generic 'not valid' message."""
    visitor = pre_register(resident_client).get_json()['visitor']
    pass_code = visitor['pass_code']

    security_client.patch(f"/api/visitors/{visitor['id']}/checkin")

    revoke = resident_client.patch(f"/api/visitors/{visitor['id']}/revoke")
    assert revoke.status_code == 200

    r = security_client.patch('/api/visitors/verify', json={'pass_code': pass_code})
    assert r.status_code == 200
    body = r.get_json()['visitor']
    assert body['status'] == 'checked_in'
    assert body['is_expired'] is True  # still reported as revoked for context


def test_verify_checked_out_visitor_shows_already_used_even_if_pass_revoked(resident_client, security_client):
    visitor = pre_register(resident_client).get_json()['visitor']
    pass_code = visitor['pass_code']

    security_client.patch(f"/api/visitors/{visitor['id']}/checkin")
    security_client.patch(f"/api/visitors/{visitor['id']}/checkout")
    resident_client.patch(f"/api/visitors/{visitor['id']}/revoke")

    r = security_client.patch('/api/visitors/verify', json={'pass_code': pass_code})
    assert r.status_code == 200
    assert r.get_json()['visitor']['status'] == 'checked_out'


def test_verify_revoked_never_checked_in_pass_says_not_valid(resident_client, security_client):
    visitor = pre_register(resident_client).get_json()['visitor']
    pass_code = visitor['pass_code']

    resident_client.patch(f"/api/visitors/{visitor['id']}/revoke")

    r = security_client.patch('/api/visitors/verify', json={'pass_code': pass_code})
    assert r.status_code == 404
    assert r.get_json()['error'] == 'This pass is not valid'


def test_checkin_on_revoked_but_already_checked_in_visitor_reports_already_in(resident_client, security_client):
    visitor = pre_register(resident_client).get_json()['visitor']

    security_client.patch(f"/api/visitors/{visitor['id']}/checkin")
    resident_client.patch(f"/api/visitors/{visitor['id']}/revoke")

    r = security_client.patch(f"/api/visitors/{visitor['id']}/checkin")
    assert r.status_code == 400
    assert 'already checked in' in r.get_json()['error']


def test_security_can_check_in_visitor(resident_client, security_client):
    visitor = pre_register(resident_client).get_json()['visitor']

    r = security_client.patch(f"/api/visitors/{visitor['id']}/checkin")
    assert r.status_code == 200
    updated = r.get_json()['visitor']
    assert updated['status'] == 'checked_in'
    assert updated['id_verified'] is True
    assert updated['check_in_time'] is not None