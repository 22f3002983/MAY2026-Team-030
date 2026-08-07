def submit_request(client, **overrides):
    payload = {'name': 'New Name', 'phone': '9123456780'}
    payload.update(overrides)
    return client.post('/api/profile-requests', json=payload)


def test_resident_can_submit_request(resident_client):
    r = submit_request(resident_client)
    assert r.status_code == 201
    body = r.get_json()['request']
    assert body['status'] == 'pending'
    assert body['proposed_changes']['name'] == 'New Name'


def test_no_valid_fields_rejected(resident_client):
    r = resident_client.post('/api/profile-requests', json={'not_a_field': 'x'})
    assert r.status_code == 400


def test_invalid_occupant_type_rejected(resident_client):
    r = submit_request(resident_client, occupant_type='landlord')
    assert r.status_code == 400


def test_duplicate_pending_request_rejected(resident_client):
    submit_request(resident_client)
    r = submit_request(resident_client, name='Another Name')
    assert r.status_code == 409


def test_secretary_can_approve_request(resident_client, secretary_client):
    req = submit_request(resident_client).get_json()['request']

    r = secretary_client.patch(f"/api/profile-requests/{req['id']}/approve")
    assert r.status_code == 200
    assert r.get_json()['request']['status'] == 'approved'

    # the resident's own profile should now reflect the change
    profile = resident_client.get('/api/profile-requests').get_json()['requests'][0]
    assert profile['current_values']['name'] == 'New Name'


def test_secretary_can_reject_request(resident_client, secretary_client):
    req = submit_request(resident_client).get_json()['request']

    r = secretary_client.patch(f"/api/profile-requests/{req['id']}/reject")
    assert r.status_code == 200
    assert r.get_json()['request']['status'] == 'rejected'


def test_cannot_review_an_already_reviewed_request(resident_client, secretary_client):
    req = submit_request(resident_client).get_json()['request']
    secretary_client.patch(f"/api/profile-requests/{req['id']}/approve")

    r = secretary_client.patch(f"/api/profile-requests/{req['id']}/reject")
    assert r.status_code == 400


def test_resident_cannot_approve_own_request(resident_client):
    req = submit_request(resident_client).get_json()['request']
    r = resident_client.patch(f"/api/profile-requests/{req['id']}/approve")
    assert r.status_code == 403