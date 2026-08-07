import pytest


import app.routes.electricity_bills as electricity_bills_module


# NOTE: conftest.py's shared `resident_client` fixture doesn't pass the
# tower/floor/unit_number/flat_number fields resident registration requires,
# so it silently 400s and never logs in. Overridden here so these tests
# actually exercise an authenticated resident.




@pytest.fixture()
def resident_client(app):
    c = app.test_client()
    reg = c.post('/api/auth/register', json={
        'email': 'resident@test.com', 'password': 'Passw0rd1', 'role': 'resident',
        'name': 'Res Ident', 'phone': '9000000001',
        'tower': 'A', 'floor': 1, 'unit_number': '101', 'flat_number': 'A-101',
    })
    # a resident's FIRST login requires the invite code issued at registration
    invite_code = reg.get_json()['invite_code']
    c.post('/api/auth/login', json={'email': 'resident@test.com', 'password': 'Passw0rd1', 'invite_code': invite_code})
    return c




def create_bill(client, month, units=500, amount=4500):
    return client.post('/api/electricity-bills', json={
        'month': month, 'total_units': units, 'total_amount': amount,
    })




# ── POST /api/electricity-bills ──────────────────────────────────


def test_create_bill_resident_forbidden(resident_client):
    res = create_bill(resident_client, '2026-07')
    assert res.status_code == 403




def test_create_bill_requires_fields(secretary_client):
    res = secretary_client.post('/api/electricity-bills', json={'month': '2026-07'})
    assert res.status_code == 400




def test_create_bill_stores_ai_analysis(secretary_client, monkeypatch):
    monkeypatch.setattr(
        electricity_bills_module, 'analyze_electricity_bill',
        lambda current, previous: 'Usage is 10% above the recent average.',
    )
    res = create_bill(secretary_client, '2026-07')
    assert res.status_code == 201
    assert res.get_json()['bill']['ai_analysis'] == 'Usage is 10% above the recent average.'




def test_create_bill_no_analysis_available(secretary_client, monkeypatch):
    monkeypatch.setattr(electricity_bills_module, 'analyze_electricity_bill', lambda current, previous: None)
    res = create_bill(secretary_client, '2026-07')
    assert res.status_code == 201
    assert res.get_json()['bill']['ai_analysis'] is None




def test_comparison_picks_3_most_recent_bills_regardless_of_upload_order(secretary_client, monkeypatch):
    """Regression test for a fixed bug: the comparison used to only look at
    bills strictly before the new one chronologically, so a bill entered
    out of order got no context. It should always compare against the 3
    most recent OTHER bills on record, however they were uploaded."""
    captured = {}


    def fake_analyze(current, previous):
        captured['previous'] = [p['month'] for p in previous]
        return 'ok'


    monkeypatch.setattr(electricity_bills_module, 'analyze_electricity_bill', fake_analyze)


    # seed out of chronological order: Jan, then June, then March
    create_bill(secretary_client, '2026-01')
    create_bill(secretary_client, '2026-06')
    create_bill(secretary_client, '2026-03')


    # a Feb bill (older than June/March, newer than Jan) should still
    # compare against the 3 most recent overall (Jun, Mar, Jan)
    create_bill(secretary_client, '2026-02')


    assert captured['previous'] == ['2026-06-01', '2026-03-01', '2026-01-01']




def test_create_bill_accepts_yyyy_mm_month_format(secretary_client, monkeypatch):
    monkeypatch.setattr(electricity_bills_module, 'analyze_electricity_bill', lambda current, previous: None)
    res = create_bill(secretary_client, '2026-07')
    assert res.status_code == 201
    assert res.get_json()['bill']['month'] == '2026-07-01'




def test_create_bill_rejects_bad_month_format(secretary_client):
    res = secretary_client.post('/api/electricity-bills', json={
        'month': 'not-a-month', 'total_units': 100, 'total_amount': 1000,
    })
    assert res.status_code == 400




# ── GET /api/electricity-bills ───────────────────────────────────


def test_list_bills_resident_forbidden(resident_client):
    res = resident_client.get('/api/electricity-bills')
    assert res.status_code == 403




def test_list_bills_secretary_ok(secretary_client, monkeypatch):
    monkeypatch.setattr(electricity_bills_module, 'analyze_electricity_bill', lambda current, previous: None)
    create_bill(secretary_client, '2026-07')
    res = secretary_client.get('/api/electricity-bills')
    assert res.status_code == 200
    assert res.get_json()['total'] == 1




# ── GET /api/electricity-bills/<id>/analysis ─────────────────────


def test_get_analysis_returns_stored_value(secretary_client, monkeypatch):
    monkeypatch.setattr(electricity_bills_module, 'analyze_electricity_bill', lambda current, previous: 'All good.')
    bill_id = create_bill(secretary_client, '2026-07').get_json()['bill']['id']


    res = secretary_client.get(f'/api/electricity-bills/{bill_id}/analysis')
    assert res.status_code == 200
    assert res.get_json() == {'ai_analysis': 'All good.'}




def test_get_analysis_resident_forbidden(secretary_client, resident_client, monkeypatch):
    monkeypatch.setattr(electricity_bills_module, 'analyze_electricity_bill', lambda current, previous: None)
    bill_id = create_bill(secretary_client, '2026-07').get_json()['bill']['id']


    res = resident_client.get(f'/api/electricity-bills/{bill_id}/analysis')
    assert res.status_code == 403



