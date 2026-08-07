def test_resident_cannot_view_funds(resident_client):
    r = resident_client.get('/api/funds')
    assert r.status_code == 403


def test_default_config_sums_to_100(secretary_client):
    r = secretary_client.get('/api/funds/config')
    assert r.status_code == 200
    configs = r.get_json()['config']
    assert round(sum(c['percentage'] for c in configs if c['is_active']), 2) == 100
    assert {c['fund_name'] for c in configs} == {'operating', 'sinking', 'contingency'}


def test_single_update_rejected_if_it_breaks_100(secretary_client):
    configs = secretary_client.get('/api/funds/config').get_json()['config']
    operating = next(c for c in configs if c['fund_name'] == 'operating')

    r = secretary_client.patch(f"/api/funds/config/{operating['id']}", json={'percentage': 50})
    assert r.status_code == 400


def test_bulk_update_changes_the_split(secretary_client):
    configs = secretary_client.get('/api/funds/config').get_json()['config']
    updates = []
    for c in configs:
        pct = {'operating': 50, 'sinking': 30, 'contingency': 20}[c['fund_name']]
        updates.append({'id': c['id'], 'percentage': pct, 'is_active': True})

    r = secretary_client.patch('/api/funds/config', json={'configs': updates})
    assert r.status_code == 200
    new_configs = {c['fund_name']: c['percentage'] for c in r.get_json()['config']}
    assert new_configs == {'operating': 50, 'sinking': 30, 'contingency': 20}


def test_credit_transaction_splits_across_funds(secretary_client):
    r = secretary_client.post('/api/funds/transactions', json={
        'type': 'credit', 'amount': 1000, 'description': 'Test credit',
    })
    assert r.status_code == 201
    balances = {f['fund_name']: f['balance'] for f in r.get_json()['funds']}
    assert balances['operating']   == 700.0
    assert balances['sinking']     == 200.0
    assert balances['contingency'] == 100.0


def test_debit_from_operating_when_available(secretary_client):
    secretary_client.post('/api/funds/transactions', json={
        'type': 'credit', 'amount': 1000, 'description': 'Seed funds',
    })
    r = secretary_client.post('/api/funds/transactions', json={
        'type': 'debit', 'amount': 100, 'description': 'Test debit', 'fund_name': 'operating',
    })
    assert r.status_code == 201
    assert r.get_json()['fund']['balance'] == 600.0


def test_debit_blocked_from_other_fund_while_operating_has_balance(secretary_client):
    secretary_client.post('/api/funds/transactions', json={
        'type': 'credit', 'amount': 1000, 'description': 'Seed funds',
    })
    r = secretary_client.post('/api/funds/transactions', json={
        'type': 'debit', 'amount': 50, 'description': 'Test debit', 'fund_name': 'sinking',
    })
    assert r.status_code == 400
    assert 'operating' in r.get_json()['error'].lower()