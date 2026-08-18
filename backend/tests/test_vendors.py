def add_vendor(client, **overrides):
    payload = {'name': 'Kishore Plumbing', 'phone': '9900011122', 'category': 'plumber'}
    payload.update(overrides)
    return client.post('/api/vendors', json=payload)


def test_secretary_can_add_vendor(secretary_client):
    r = add_vendor(secretary_client)
    assert r.status_code == 201
    body = r.get_json()['vendor']
    assert body['name'] == 'Kishore Plumbing'
    assert body['status'] == 'active'
    assert body['is_salaried'] is False


def test_resident_cannot_add_vendor(resident_client):
    r = add_vendor(resident_client)
    assert r.status_code == 403


def test_list_vendors_defaults_to_active_only(secretary_client):
    v1 = add_vendor(secretary_client, name='Active Vendor', phone='9000000010').get_json()['vendor']
    v2 = add_vendor(secretary_client, name='Inactive Vendor', phone='9000000011').get_json()['vendor']
    secretary_client.patch(f"/api/vendors/{v2['id']}", json={'status': 'inactive'})

    r = secretary_client.get('/api/vendors')
    names = [v['name'] for v in r.get_json()['vendors']]
    assert 'Active Vendor' in names
    assert 'Inactive Vendor' not in names


def test_pay_salaries_debits_operating_fund_and_records_transaction(secretary_client):
    # seed the operating fund with a manual credit so there's something to pay from
    secretary_client.post('/api/funds/transactions', json={
        'type': 'credit', 'amount': 100000, 'description': 'Opening balance',
    })

    vendor = add_vendor(secretary_client, name='Ramesh Gardener', phone='9000000099',
                         is_salaried=True, salary=12000).get_json()['vendor']

    r = secretary_client.post('/api/vendors/pay-salaries', json={'vendor_ids': [vendor['id']]})
    assert r.status_code == 201
    body = r.get_json()
    assert body['paid_count'] == 1
    assert body['total_paid'] == 12000

    funds = secretary_client.get('/api/funds').get_json()['funds']
    operating = next(f for f in funds if f['fund_name'] == 'operating')
    # 70% of 100000 = 70000 credited, minus 12000 salary debit
    assert operating['balance'] == 58000

    txns = secretary_client.get('/api/funds/transactions?source=vendor_salary').get_json()['transactions']
    assert len(txns) == 1
    assert txns[0]['type'] == 'debit'
    assert txns[0]['amount'] == 12000
    assert txns[0]['reference_id'] == vendor['id']
    assert txns[0]['fund_name'] == 'operating'


def test_pay_salaries_preview_shows_fund_breakdown(secretary_client):
    secretary_client.post('/api/funds/transactions', json={
        'type': 'credit', 'amount': 100000, 'description': 'Opening balance',
    })
    vendor = add_vendor(secretary_client, name='Preview Vendor', phone='9000000096',
                         is_salaried=True, salary=5000).get_json()['vendor']

    r = secretary_client.post('/api/vendors/pay-salaries/preview', json={'vendor_ids': [vendor['id']]})
    assert r.status_code == 200
    body = r.get_json()
    assert body['sufficient'] is True
    assert body['shortfall'] == 0
    operating = next(f for f in body['funds'] if f['fund_name'] == 'operating')
    assert operating['balance_before'] == 70000
    assert operating['amount_drawn'] == 5000
    assert operating['balance_after'] == 65000

    # preview must not have actually debited anything
    funds = secretary_client.get('/api/funds').get_json()['funds']
    assert next(f for f in funds if f['fund_name'] == 'operating')['balance'] == 70000


def test_pay_salaries_cascades_to_contingency_when_operating_short(secretary_client):
    # operating gets 70% = 700, contingency gets 10% = 100, sinking 20% = 200
    secretary_client.post('/api/funds/transactions', json={
        'type': 'credit', 'amount': 1000, 'description': 'Opening balance',
    })
    vendor = add_vendor(secretary_client, name='Big Salary Vendor', phone='9000000095',
                         is_salaried=True, salary=750).get_json()['vendor']

    r = secretary_client.post('/api/vendors/pay-salaries', json={'vendor_ids': [vendor['id']]})
    assert r.status_code == 201

    txns = secretary_client.get('/api/funds/transactions?source=vendor_salary').get_json()['transactions']
    # 700 needed from operating (has exactly 700) + 50 more from contingency
    assert len(txns) == 2
    by_fund = {t['fund_name']: t['amount'] for t in txns}
    assert by_fund['operating'] == 700
    assert by_fund['contingency'] == 50

    funds = secretary_client.get('/api/funds').get_json()['funds']
    assert next(f for f in funds if f['fund_name'] == 'operating')['balance'] == 0
    assert next(f for f in funds if f['fund_name'] == 'contingency')['balance'] == 50


def test_pay_salaries_shortfall_across_all_three_funds_blocks_payment(secretary_client):
    secretary_client.post('/api/funds/transactions', json={
        'type': 'credit', 'amount': 1000, 'description': 'Opening balance',
    })
    vendor = add_vendor(secretary_client, name='Too Expensive Vendor', phone='9000000094',
                         is_salaried=True, salary=5000).get_json()['vendor']

    r = secretary_client.post('/api/vendors/pay-salaries', json={'vendor_ids': [vendor['id']]})
    assert r.status_code == 400
    assert 'shortfall' in r.get_json()

    # nothing should have been debited
    funds = secretary_client.get('/api/funds').get_json()['funds']
    assert next(f for f in funds if f['fund_name'] == 'operating')['balance'] == 700


def test_pay_salaries_rejects_non_salaried_vendor(secretary_client):
    vendor = add_vendor(secretary_client, name='Non Salaried', phone='9000000098').get_json()['vendor']
    r = secretary_client.post('/api/vendors/pay-salaries', json={'vendor_ids': [vendor['id']]})
    assert r.status_code == 400


def test_toggle_vendor_status(secretary_client):
    vendor = add_vendor(secretary_client).get_json()['vendor']

    r = secretary_client.patch(f"/api/vendors/{vendor['id']}", json={'status': 'inactive'})
    assert r.status_code == 200
    assert r.get_json()['vendor']['status'] == 'inactive'

    r2 = secretary_client.patch(f"/api/vendors/{vendor['id']}", json={'status': 'active'})
    assert r2.get_json()['vendor']['status'] == 'active'


def test_invalid_category_rejected(secretary_client):
    r = add_vendor(secretary_client, category='not-a-real-category')
    assert r.status_code == 400