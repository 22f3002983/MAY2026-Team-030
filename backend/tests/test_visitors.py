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


# ── multi-use / one-time-use passes ─────────────────────────────

def test_pre_registered_pass_defaults_to_multi_use(resident_client):
    visitor = pre_register(resident_client).get_json()['visitor']
    assert visitor['is_multi_use'] is True
    assert visitor['valid_until'] is None


def test_one_time_use_pass_requires_expected_date(resident_client):
    r = pre_register(resident_client, is_multi_use=False)
    assert r.status_code == 400
    assert 'Expected date is required' in r.get_json()['error']


def test_one_time_use_pass_with_expected_date_succeeds(resident_client):
    r = pre_register(resident_client, is_multi_use=False, expected_date='2026-09-15')
    assert r.status_code == 201
    visitor = r.get_json()['visitor']
    assert visitor['is_multi_use'] is False
    assert visitor['expires_at'].startswith('2026-09-15')


def test_multi_use_pass_does_not_require_expected_date(resident_client):
    r = pre_register(resident_client, is_multi_use=True)
    assert r.status_code == 201
    visitor = r.get_json()['visitor']
    assert visitor['expected_date'] is None
    assert visitor['expires_at'] is None  # open-ended, no valid_until given


def test_multi_use_pass_expires_at_end_of_valid_until_day(resident_client):
    r = pre_register(resident_client, is_multi_use=True, valid_until='2026-12-31')
    assert r.status_code == 201
    visitor = r.get_json()['visitor']
    assert visitor['valid_until'] == '2026-12-31'
    assert visitor['expires_at'].startswith('2026-12-31T23:59:59')


def test_one_time_use_pass_cannot_be_reused_after_checkout(resident_client, security_client):
    visitor = pre_register(resident_client, is_multi_use=False, expected_date='2026-09-15').get_json()['visitor']

    security_client.patch(f"/api/visitors/{visitor['id']}/checkin")
    security_client.patch(f"/api/visitors/{visitor['id']}/checkout")

    r = security_client.patch('/api/visitors/verify', json={'pass_code': visitor['pass_code']})
    # status is checked_out, so verify still reports it (status takes
    # priority) but a fresh check-in attempt must be rejected
    checkin_again = security_client.patch(f"/api/visitors/{visitor['id']}/checkin")
    assert checkin_again.status_code == 400
    assert checkin_again.get_json()['error'] == 'This pass is not valid'


def test_multi_use_pass_can_be_checked_in_again_after_checkout(resident_client, security_client):
    visitor = pre_register(resident_client, is_multi_use=True).get_json()['visitor']

    security_client.patch(f"/api/visitors/{visitor['id']}/checkin")
    security_client.patch(f"/api/visitors/{visitor['id']}/checkout")

    r = security_client.patch(f"/api/visitors/{visitor['id']}/checkin")
    assert r.status_code == 200
    assert r.get_json()['visitor']['status'] == 'checked_in'


# ── validity_mode (exact_date / until_date / no_date) ───────────
# Independent of is_multi_use — either use-type can pick any of these.

def test_exact_date_mode_requires_expected_date(resident_client):
    r = pre_register(resident_client, validity_mode='exact_date')
    assert r.status_code == 400
    assert 'Expected date is required' in r.get_json()['error']


def test_until_date_mode_requires_expected_date(resident_client):
    r = pre_register(resident_client, validity_mode='until_date')
    assert r.status_code == 400
    assert 'Expected date is required' in r.get_json()['error']


def test_no_date_mode_does_not_require_expected_date_even_for_one_time_use(resident_client):
    r = pre_register(resident_client, is_multi_use=False, validity_mode='no_date')
    assert r.status_code == 201
    visitor = r.get_json()['visitor']
    assert visitor['is_multi_use'] is False
    assert visitor['expected_date'] is None
    assert visitor['expires_at'] is None  # open-ended, no valid_until given


def test_exact_date_pass_cannot_be_checked_in_before_expected_date(resident_client, security_client):
    future_date = '2099-01-01'
    visitor = pre_register(resident_client, validity_mode='exact_date', expected_date=future_date).get_json()['visitor']

    r = security_client.patch(f"/api/visitors/{visitor['id']}/checkin")
    assert r.status_code == 400
    assert "isn't valid yet" in r.get_json()['error']


def test_exact_date_pass_verify_reports_not_yet_valid(resident_client, security_client):
    future_date = '2099-01-01'
    visitor = pre_register(resident_client, validity_mode='exact_date', expected_date=future_date).get_json()['visitor']

    r = security_client.patch('/api/visitors/verify', json={'pass_code': visitor['pass_code']})
    assert r.status_code == 404
    assert "isn't valid yet" in r.get_json()['error']


def test_until_date_pass_can_be_checked_in_before_expected_date(resident_client, security_client):
    future_date = '2099-01-01'
    visitor = pre_register(resident_client, validity_mode='until_date', expected_date=future_date).get_json()['visitor']

    r = security_client.patch(f"/api/visitors/{visitor['id']}/checkin")
    assert r.status_code == 200
    assert r.get_json()['visitor']['status'] == 'checked_in'


# ── check-in / check-out notifications ──────────────────────────

def test_checkin_notifies_resident(resident_client, security_client):
    visitor = pre_register(resident_client).get_json()['visitor']

    security_client.patch(f"/api/visitors/{visitor['id']}/checkin")

    notifs = resident_client.get('/api/notifications').get_json()['notifications']
    assert any(n['type'] == 'visitor_checked_in' and visitor['name'] in n['message'] for n in notifs)


def test_checkout_notifies_resident(resident_client, security_client):
    visitor = pre_register(resident_client).get_json()['visitor']

    security_client.patch(f"/api/visitors/{visitor['id']}/checkin")
    security_client.patch(f"/api/visitors/{visitor['id']}/checkout")

    notifs = resident_client.get('/api/notifications').get_json()['notifications']
    assert any(n['type'] == 'visitor_checked_out' and visitor['name'] in n['message'] for n in notifs)


# ── PATCH /api/visitors/<id>/schedule — editing an existing pass ────

def test_resident_can_update_expected_date_and_time(resident_client):
    visitor = pre_register(resident_client, validity_mode='until_date', expected_date='2026-09-10').get_json()['visitor']

    r = resident_client.patch(f"/api/visitors/{visitor['id']}/schedule", json={
        'expected_date': '2026-09-20',
        'expected_time': '14:30',
    })
    assert r.status_code == 200
    updated = r.get_json()['visitor']
    assert updated['expected_date'] == '2026-09-20'
    assert updated['expected_time'].startswith('14:30')
    assert updated['expires_at'].startswith('2026-09-20T23:59:59')


def test_resident_can_update_valid_until_on_no_date_pass(resident_client):
    visitor = pre_register(resident_client, is_multi_use=True, validity_mode='no_date').get_json()['visitor']

    r = resident_client.patch(f"/api/visitors/{visitor['id']}/schedule", json={'valid_until': '2026-12-25'})
    assert r.status_code == 200
    updated = r.get_json()['visitor']
    assert updated['valid_until'] == '2026-12-25'
    assert updated['expires_at'].startswith('2026-12-25T23:59:59')


def test_resident_can_clear_expected_time_only(resident_client):
    visitor = pre_register(
        resident_client, validity_mode='until_date', expected_date='2026-09-10', expected_time='09:00'
    ).get_json()['visitor']

    r = resident_client.patch(f"/api/visitors/{visitor['id']}/schedule", json={'expected_time': None})
    assert r.status_code == 200
    updated = r.get_json()['visitor']
    assert updated['expected_time'] is None
    assert updated['expected_date'] == '2026-09-10'  # untouched


def test_cannot_clear_expected_date_when_required_by_validity_mode(resident_client):
    visitor = pre_register(resident_client, validity_mode='exact_date', expected_date='2026-09-10').get_json()['visitor']

    r = resident_client.patch(f"/api/visitors/{visitor['id']}/schedule", json={'expected_date': None})
    assert r.status_code == 400
    assert 'Expected date is required' in r.get_json()['error']


def test_other_resident_cannot_edit_someone_elses_pass(resident_client, resident_client_2):
    visitor = pre_register(resident_client).get_json()['visitor']

    r = resident_client_2.patch(f"/api/visitors/{visitor['id']}/schedule", json={'expected_date': '2026-09-20'})
    assert r.status_code == 403


def test_cannot_edit_a_walk_in_pass(resident_client):
    visitor = pre_register(resident_client, visit_type='walk_in').get_json()['visitor']

    r = resident_client.patch(f"/api/visitors/{visitor['id']}/schedule", json={'expected_date': '2026-09-20'})
    assert r.status_code == 400
    assert 'Only pre-registered passes' in r.get_json()['error']


def test_cannot_edit_a_checked_in_pass(resident_client, security_client):
    visitor = pre_register(resident_client).get_json()['visitor']
    security_client.patch(f"/api/visitors/{visitor['id']}/checkin")

    r = resident_client.patch(f"/api/visitors/{visitor['id']}/schedule", json={'expected_date': '2026-09-20'})
    assert r.status_code == 400
    assert "hasn't been used yet" in r.get_json()['error']


def test_cannot_edit_a_revoked_pass(resident_client):
    visitor = pre_register(resident_client).get_json()['visitor']
    resident_client.patch(f"/api/visitors/{visitor['id']}/revoke")

    r = resident_client.patch(f"/api/visitors/{visitor['id']}/schedule", json={'expected_date': '2026-09-20'})
    assert r.status_code == 400
    assert 'revoked' in r.get_json()['error']


# ── GET /api/visitors/today?date=... ────────────────────────────

def test_today_endpoint_filters_by_given_date(resident_client, secretary_client):
    matching    = pre_register(resident_client, name='Matching Visitor', validity_mode='until_date', expected_date='2026-10-05').get_json()['visitor']
    non_matching = pre_register(resident_client, name='Other Visitor', validity_mode='until_date', expected_date='2026-10-06').get_json()['visitor']

    r = secretary_client.get('/api/visitors/today?date=2026-10-05')
    assert r.status_code == 200
    names = [v['name'] for v in r.get_json()['visitors']]
    assert 'Matching Visitor' in names
    assert 'Other Visitor' not in names


def test_today_endpoint_includes_flat_details_for_secretary(resident_client, secretary_client):
    visitor = pre_register(resident_client, validity_mode='until_date', expected_date='2026-10-05').get_json()['visitor']

    r = secretary_client.get('/api/visitors/today?date=2026-10-05')
    result = next(v for v in r.get_json()['visitors'] if v['id'] == visitor['id'])
    assert 'flat_number' in result
    assert 'tower' in result


def test_today_endpoint_rejects_bad_date_format(secretary_client):
    r = secretary_client.get('/api/visitors/today?date=not-a-date')
    assert r.status_code == 400