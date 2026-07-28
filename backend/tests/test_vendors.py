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
