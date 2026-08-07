def test_resident_can_update_profile(resident_client):
    r = resident_client.patch('/api/profile', json={'name': 'Updated Name', 'phone': '9123456789'})
    assert r.status_code == 200
    assert r.get_json()['message'] == 'Profile updated successfully'


def test_no_data_rejected(resident_client):
    r = resident_client.patch('/api/profile', json={})
    assert r.status_code == 400


def test_secretary_cannot_use_resident_profile_route(secretary_client):
    r = secretary_client.patch('/api/profile', json={'name': 'Nope'})
    assert r.status_code == 403